"""
Service de gestion des déploiements Docker.

Refactor :
 - lié à l'utilisateur (via CRUD)
 - historique via Build
 - actions container (start/stop/restart/remove/rebuild)
 - détection basique du type d'application (web / api / cli)
 - URL générée localement http://<host>:<port>
"""

import logging
import os
import re
import shutil
import subprocess
import tempfile
import zipfile
from typing import Optional

import docker
import git
from sqlalchemy.orm import Session

from app import crud
from app.core.config import settings
from app.models.build import Build
from app.models.deployment import Deployment

logger = logging.getLogger(__name__)


# Ports fréquemment exposés par les apps web/API
WEB_PORTS = {80, 3000, 4000, 5000, 8000, 8080, 8888}


class DeploymentService:
    def __init__(self, db: Session):
        self.db = db
        try:
            self.docker_client = docker.from_env()
        except Exception as exc:
            logger.warning("Docker indisponible : %s", exc)
            self.docker_client = None

    # ---------- helpers ----------

    def _require_docker(self):
        if not self.docker_client:
            raise RuntimeError("Docker is not available on this host")

    def _create_temp_dir(self) -> str:
        return tempfile.mkdtemp(prefix="deployhub_")

    @staticmethod
    def _get_compose_file(path: str) -> Optional[str]:
        for filename in ("docker-compose.yml", "docker-compose.yaml"):
            full = os.path.join(path, filename)
            if os.path.exists(full):
                return full
        return None

    @staticmethod
    def _validate_dockerfile(path: str) -> str:
        dockerfile_path = os.path.join(path, "Dockerfile")
        if not os.path.exists(dockerfile_path):
            raise ValueError("No Dockerfile (or docker-compose.yml) found in project root.")
        return dockerfile_path

    @staticmethod
    def _detect_exposed_port(dockerfile_path: str) -> Optional[int]:
        try:
            with open(dockerfile_path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    m = re.match(r"\s*EXPOSE\s+(\d+)", line, re.IGNORECASE)
                    if m:
                        return int(m.group(1))
        except OSError:
            return None
        return None

    @staticmethod
    def _detect_app_type(exposed_port: Optional[int], dockerfile_path: Optional[str]) -> str:
        if exposed_port and exposed_port in WEB_PORTS:
            return "web"
        if dockerfile_path and os.path.exists(dockerfile_path):
            try:
                with open(dockerfile_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read().lower()
                if any(k in content for k in ("fastapi", "uvicorn", "flask", "express", "gunicorn", "django")):
                    return "api"
            except OSError:
                pass
        return "cli"

    def _get_available_port(self) -> int:
        self._require_docker()
        used_ports = set()
        for container in self.docker_client.containers.list(all=True):
            ports = container.attrs.get("NetworkSettings", {}).get("Ports", {}) or {}
            for bindings in ports.values():
                if not bindings:
                    continue
                for binding in bindings:
                    host_port = binding.get("HostPort")
                    if host_port:
                        used_ports.add(int(host_port))

        for port in range(settings.DEPLOY_PORT_RANGE_START, settings.DEPLOY_PORT_RANGE_END):
            if port not in used_ports:
                return port
        raise RuntimeError("No available ports in configured range")

    # ---------- main pipeline ----------

    def execute_deployment(self, deployment_id: int) -> Deployment:
        """Pipeline complet : clone/unzip → build → run. Crée un Build associé."""
        deployment = crud.deployment.get(self.db, deployment_id=deployment_id)
        if not deployment:
            raise ValueError(f"Deployment {deployment_id} not found")

        build = crud.deployment.create_build(self.db, deployment_id=deployment.id)
        temp_dir = self._create_temp_dir()
        build_logs: list = []

        try:
            # 1. Récupération du code
            if deployment.source_type == "github":
                crud.deployment.set_status(self.db, deployment=deployment, status="cloning")
                build_logs.append(f"Cloning {deployment.source_url} (branch={deployment.branch})...")
                git.Repo.clone_from(
                    deployment.source_url, temp_dir, branch=deployment.branch or "main"
                )
            else:
                crud.deployment.set_status(self.db, deployment=deployment, status="extracting")
                build_logs.append(f"Extracting archive {deployment.source_url}...")
                with zipfile.ZipFile(deployment.source_url, "r") as zf:
                    zf.extractall(temp_dir)

            # 2. Build & run
            self._build_and_run(deployment, temp_dir, build, build_logs)

            crud.deployment.finalize_build(
                self.db,
                build=build,
                status="success",
                logs="\n".join(build_logs),
            )
            return deployment

        except Exception as exc:
            error = str(exc)
            logger.exception("Deployment %s failed", deployment_id)
            build_logs.append(f"ERROR: {error}")
            crud.deployment.set_status(
                self.db, deployment=deployment, status="failed", error_message=error
            )
            crud.deployment.finalize_build(
                self.db,
                build=build,
                status="failed",
                error_message=error,
                logs="\n".join(build_logs),
            )
            raise
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def _build_and_run(
        self,
        deployment: Deployment,
        path: str,
        build: Build,
        build_logs: list,
    ) -> None:
        compose_file = self._get_compose_file(path)

        if compose_file:
            deployment.is_compose = True
            crud.deployment.set_status(self.db, deployment=deployment, status="building")
            project_name = f"deployhub-{deployment.id}"
            env = os.environ.copy()
            if deployment.env_vars:
                env.update({k: str(v) for k, v in deployment.env_vars.items()})
            try:
                result = subprocess.run(
                    ["docker", "compose", "-p", project_name, "up", "-d", "--build"],
                    cwd=path,
                    check=True,
                    capture_output=True,
                    text=True,
                    env=env,
                )
                build_logs.append(result.stdout or "")
                build_logs.append(result.stderr or "")
            except subprocess.CalledProcessError as e:
                raise RuntimeError(f"Docker Compose failed: {e.stderr or e.stdout}") from e

            deployment.app_type = "web"
            deployment.image_tag = project_name
            deployment.app_url = f"compose://{project_name}"
            crud.deployment.set_status(self.db, deployment=deployment, status="running")
            return

        # --- Dockerfile path ---
        self._require_docker()
        dockerfile_path = self._validate_dockerfile(path)
        exposed_port = self._detect_exposed_port(dockerfile_path)
        app_type = self._detect_app_type(exposed_port, dockerfile_path)

        crud.deployment.set_status(self.db, deployment=deployment, status="building")
        image_tag = f"deployhub-{deployment.slug}:latest"
        build_logs.append(f"Building image {image_tag}...")

        image, raw_logs = self.docker_client.images.build(path=path, tag=image_tag, rm=True)
        for chunk in raw_logs:
            if isinstance(chunk, dict) and "stream" in chunk:
                build_logs.append(chunk["stream"].rstrip())

        deployment.image_id = image.id
        deployment.image_tag = image_tag
        deployment.app_type = app_type

        crud.deployment.set_status(self.db, deployment=deployment, status="starting")

        run_kwargs = dict(
            detach=True,
            environment=deployment.env_vars or {},
            name=f"deployhub-{deployment.slug}",
            labels={"deployhub.deployment_id": str(deployment.id)},
        )
        if exposed_port:
            host_port = self._get_available_port()
            run_kwargs["ports"] = {f"{exposed_port}/tcp": host_port}
            deployment.port = host_port
            deployment.app_url = f"http://{settings.DEPLOY_HOST}:{host_port}"
        else:
            deployment.app_url = None

        container = self.docker_client.containers.run(image_tag, **run_kwargs)
        deployment.container_id = container.id
        build_logs.append(f"Container started: {container.short_id}")

        crud.deployment.set_status(self.db, deployment=deployment, status="running")

    # ---------- actions ----------

    def _get_container(self, deployment: Deployment):
        self._require_docker()
        if not deployment.container_id:
            return None
        try:
            return self.docker_client.containers.get(deployment.container_id)
        except docker.errors.NotFound:
            return None

    def stop(self, deployment: Deployment) -> Deployment:
        container = self._get_container(deployment)
        if container:
            try:
                container.stop(timeout=10)
            except Exception as exc:
                logger.warning("Stop failed: %s", exc)
        return crud.deployment.set_status(self.db, deployment=deployment, status="stopped")

    def restart(self, deployment: Deployment) -> Deployment:
        container = self._get_container(deployment)
        if not container:
            raise ValueError("No container associated with this deployment")
        container.restart(timeout=10)
        return crud.deployment.set_status(self.db, deployment=deployment, status="running")

    def remove(self, deployment: Deployment) -> None:
        container = self._get_container(deployment)
        if container:
            try:
                container.remove(force=True)
            except Exception as exc:
                logger.warning("Container remove failed: %s", exc)
        if deployment.image_tag and self.docker_client:
            try:
                self.docker_client.images.remove(deployment.image_tag, force=True)
            except Exception as exc:
                logger.warning("Image remove failed: %s", exc)
        crud.deployment.remove(self.db, deployment=deployment)

    def get_container_logs(self, deployment: Deployment, tail: int = 500) -> str:
        container = self._get_container(deployment)
        if not container:
            return ""
        try:
            return container.logs(tail=tail).decode("utf-8", errors="ignore")
        except Exception as exc:
            logger.warning("Logs fetch failed: %s", exc)
            return ""


def save_upload(upload_file, suffix: str = ".zip") -> str:
    """Persist un fichier uploadé dans un endroit accessible au worker."""
    fd, temp_path = tempfile.mkstemp(prefix="deployhub_upload_", suffix=suffix)
    with os.fdopen(fd, "wb") as buf:
        shutil.copyfileobj(upload_file, buf)
    return temp_path
