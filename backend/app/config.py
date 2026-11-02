"""Application configuration loaded from environment variables."""

from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """Application settings schema with default fallback values."""
    
    # API Secrets & Models
    gemini_api_key: str = Field(default="", validation_alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-2.5-flash", validation_alias="GEMINI_MODEL")


    # Server Configuration
    host: str = Field(default="127.0.0.1", validation_alias="HOST")
    port: int = Field(default=8000, validation_alias="PORT")
    environment: str = Field(default="development", validation_alias="ENVIRONMENT")

    # CORS configuration
    cors_origins: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173",
        validation_alias="CORS_ORIGINS"
    )

    # RAG Settings
    chroma_persist_directory: str = Field(
        default="./chroma_db",
        validation_alias="CHROMA_PERSIST_DIRECTORY"
    )
    embedding_model_name: str = Field(
        default="all-MiniLM-L6-v2",
        validation_alias="EMBEDDING_MODEL_NAME"
    )
    max_upload_size_mb: int = Field(
        default=15,
        validation_alias="MAX_UPLOAD_SIZE_MB"
    )

    model_config = SettingsConfigDict(
        env_file=(".env", str(Path(__file__).resolve().parent.parent / ".env")),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def cors_origins_list(self) -> List[str]:
        """Convert comma-separated CORS origin strings into a Python list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


# Global cached settings instance
settings = Settings()
