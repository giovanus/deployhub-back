import os
import shutil
import zipfile
import tempfile
import git
import docker
import subprocess
from sqlalchemy.orm import Session
from app.models.deployment import Deployment
from app.schemas.deployment import DeploymentCreateGithub, DeploymentCreateZip

class DeploymentService:
    def __init__(self, db: Session):
        self.db = db
        self.docker_client = docker.from_env()

    def _create_temp_dir(self):
        return tempfile.mkdtemp()

    def _get_compose_file(self, path: str):
        for filename in ["docker-compose.yml", "docker-compose.yaml"]:
            compose_path = os.path.join(path, filename)
            if os.path.exists(compose_path):
                return compose_path
        return None

    def _validate_dockerfile(self, path: str):
        dockerfile_path = os.path.join(path, "Dockerfile")
        if not os.path.exists(dockerfile_path):
            raise ValueError("No Dockerfile or docker-compose.yml found in the repository root.")
        return dockerfile_path

    def _get_available_port(self):
        used_ports = set()
        for container in self.docker_client.containers.list():
            ports = container.attrs.get('NetworkSettings', {}).get('Ports', {})
            for p_list in ports.values():
                if p_list:
                    for p in p_list:
                        used_ports.add(int(p.get('HostPort')))
        
        for port in range(8000, 9000):
            if port not in used_ports:
                return port
        raise Exception("No available ports in range 8000-9000")

    async def _execute_deployment(self, deployment: Deployment, path: str, env_vars: dict = None):
        compose_file = self._get_compose_file(path)
        
        if compose_file:
            deployment.is_compose = True
            deployment.status = "deploying_compose"
            self.db.commit()
            
            project_name = f"deployhub-{deployment.id}"
            try:
                # Prepare environment
                env = os.environ.copy()
                if env_vars:
                    env.update({k: str(v) for k, v in env_vars.items()})
                
                # Run docker compose
                subprocess.run(
                    ["docker", "compose", "-p", project_name, "up", "-d", "--build"],
                    cwd=path,
                    check=True,
                    capture_output=True,
                    text=True,
                    env=env
                )
                
                deployment.status = "running"
                # For compose, detecting the primary URL is complex. 
                # We'll just provide the project name and maybe a way to inspect it later.
                deployment.app_url = f"Compose: {project_name}"
                self.db.commit()
                return deployment
            except subprocess.CalledProcessError as e:
                deployment.status = "failed"
                self.db.commit()
                raise Exception(f"Docker Compose failed: {e.stderr}")
        else:
            # Fallback to Dockerfile logic
            self._validate_dockerfile(path)
            
            deployment.status = "building"
            self.db.commit()
            
            image_tag = f"deployhub-{deployment.id}"
            image, build_logs = self.docker_client.images.build(
                path=path,
                tag=image_tag,
                rm=True
            )
            
            deployment.image_id = image.id
            deployment.status = "starting"
            self.db.commit()
            
            host_port = self._get_available_port()
            
            container = self.docker_client.containers.run(
                image_tag,
                detach=True,
                ports={'8080/tcp': host_port},
                environment=env_vars,
                name=f"deployhub-container-{deployment.id}"
            )
            
            deployment.container_id = container.id
            deployment.port = host_port
            deployment.status = "running"
            deployment.app_url = f"http://localhost:{host_port}"
            self.db.commit()
            return deployment

    async def deploy_from_github(self, data: DeploymentCreateGithub):
        temp_dir = self._create_temp_dir()
        try:
            deployment = Deployment(
                name=data.name,
                source_type="github",
                source_url=data.github_url,
                status="cloning",
                env_vars=data.env_vars
            )
            self.db.add(deployment)
            self.db.commit()
            self.db.refresh(deployment)

            git.Repo.clone_from(data.github_url, temp_dir, branch=data.branch)
            
            return await self._execute_deployment(deployment, temp_dir, data.env_vars)

        except Exception as e:
            if 'deployment' in locals():
                deployment.status = "failed"
                self.db.commit()
            raise e
        finally:
            shutil.rmtree(temp_dir)

    async def deploy_from_zip(self, name: str, zip_path: str, env_vars: dict = None):
        temp_dir = self._create_temp_dir()
        try:
            deployment = Deployment(
                name=name,
                source_type="zip",
                status="extracting",
                env_vars=env_vars
            )
            self.db.add(deployment)
            self.db.commit()
            self.db.refresh(deployment)

            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
            return await self._execute_deployment(deployment, temp_dir, env_vars)

        except Exception as e:
            if 'deployment' in locals():
                deployment.status = "failed"
                self.db.commit()
            raise e
        finally:
            shutil.rmtree(temp_dir)
