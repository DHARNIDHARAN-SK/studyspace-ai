import json
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Application
    APP_NAME: str = "StudySpace AI API"
    APP_ENV: str = "development"
    DEBUG: bool = False
    API_PREFIX: str = "/api/v1"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    # CORS
    CORS_ORIGINS: Union[List[str], str] = ["http://localhost:5173", "http://localhost:3000"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, str) and v.startswith("["):
            try:
                return json.loads(v)
            except Exception:
                return [v]
        elif isinstance(v, (list, tuple)):
            return list(v)
        return []

    # Supabase / Database
    DATABASE_URL: str | None = None
    SUPABASE_URL: str | None = None
    SUPABASE_ANON_KEY: str | None = None
    SUPABASE_SERVICE_ROLE_KEY: str | None = None
    SUPABASE_JWT_SECRET: str | None = None

    # LLM Providers
    LLM_PROVIDER: str = "ollama"  # ollama | gemini
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_CHAT_MODEL: str = "llama3.2"
    GEMINI_API_KEY: str | None = None
    GEMINI_CHAT_MODEL: str = "gemini-1.5-flash"

    # Embeddings & Reranker
    EMBEDDING_PROVIDER: str = "ollama"
    EMBEDDING_MODEL_ID: str = "nomic-embed-text"
    EMBEDDING_VECTOR_DIMENSIONS: int = 768
    RERANKER_PROVIDER: str = "disabled"  # disabled | local | remote
    RERANKER_MODEL_ID: str | None = None

    # Background Tasks & Cache
    REDIS_URL: str | None = None

    # Limits
    MAX_UPLOAD_BYTES: int = 52428800  # 50 MB
    MAX_DOCUMENT_PAGES: int = 500


settings = Settings()
