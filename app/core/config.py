import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    PROJECT_NAME: str = "DeployHub API"
    VERSION: str = "1.0.0"
    
    SECRET_KEY: str = os.getenv("SECRET_KEY", "yoursecretkeyhere")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    
    DATABASE_URL: str = os.getenv("DATABASE_URL")

    class Config:
        case_sensitive = True

settings = Settings()
