import os
from typing import List
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


def _split_csv(value: str) -> List[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


class Settings(BaseSettings):
    PROJECT_NAME: str = os.getenv("PROJECT_NAME", "DeployHub API")
    VERSION: str = os.getenv("VERSION", "1.0.0")

    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-me-please-use-a-long-random-string")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./deployhub.db")

    BACKEND_CORS_ORIGINS: List[str] = _split_csv(
        os.getenv("BACKEND_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
    )

    DEPLOY_HOST: str = os.getenv("DEPLOY_HOST", "localhost")
    DEPLOY_PORT_RANGE_START: int = int(os.getenv("DEPLOY_PORT_RANGE_START", "8090"))
    DEPLOY_PORT_RANGE_END: int = int(os.getenv("DEPLOY_PORT_RANGE_END", "9000"))

    EMAIL_ENABLED: bool = os.getenv("EMAIL_ENABLED", "false").lower() == "true"
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:5173")

    class Config:
        case_sensitive = True


settings = Settings()

