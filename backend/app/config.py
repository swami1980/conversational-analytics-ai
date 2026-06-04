from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    anthropic_api_key: str
    jwt_secret_key: str = "dev-secret-change-in-prod"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480

    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    mock_api_base_url: str = "http://localhost:8000"

    chroma_persist_dir: str = "./chroma_db"
    sqlite_db_path: str = "./recruiting.db"

    github_token: str = "stub-token"
    github_repo: str = "owner/conversational-analytics-ai"

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
