from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ADMIN_EMAIL: str = "admin@climateview.dev"
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: Optional[str] = None

    class Config:
        env_file = ".env"

settings = Settings()