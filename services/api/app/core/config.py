import json
from pathlib import Path
from typing import List, Optional, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../../.env"),
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
    CORS_ORIGIN_REGEX: Optional[str] = r"^https:\/\/(studyspace-ai|studyspace-[a-zA-Z0-9_-]+-dharanidharan2)\.vercel\.app$"

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
    OLLAMA_CHAT_MODEL: str = "phi4-mini:latest"
    GEMINI_API_KEY: str | None = None
    GEMINI_CHAT_MODEL: str = "gemini-1.5-flash"

    # Embeddings & Reranker
    EMBEDDING_PROVIDER: str = "ollama"
    EMBEDDING_MODEL_ID: str = "nomic-embed-text:latest"
    EMBEDDING_VECTOR_DIMENSIONS: int = 768
    RERANKER_PROVIDER: str = "local"  # disabled | local | remote
    RERANKER_MODEL_ID: str | None = None

    # Baseline & Advanced RAG Settings
    RAG_RETRIEVAL_MODE: str = "advanced"  # baseline | advanced | conversational
    RAG_DEFAULT_TOP_K: int = 5
    RAG_DENSE_TOP_K: int = 20
    RAG_LEXICAL_TOP_K: int = 20
    RAG_RRF_K: int = 60
    RAG_RERANK_TOP_N: int = 5
    RAG_MAX_CONTEXT_CHARS: int = 8000

    # Phase 8: Conversational RAG, Query Transformation & Semantic Cache
    RAG_CONVERSATION_HISTORY_LIMIT: int = 6
    RAG_QUERY_REWRITE_ENABLED: bool = False
    RAG_MULTI_QUERY_ENABLED: bool = False
    RAG_MULTI_QUERY_COUNT: int = 3
    RAG_DECOMPOSITION_ENABLED: bool = False
    RAG_SEMANTIC_CACHE_ENABLED: bool = True
    RAG_SEMANTIC_CACHE_SIMILARITY_THRESHOLD: float = 0.95
    RAG_SEMANTIC_CACHE_TTL_SECONDS: int = 3600
    RAG_REQUEST_DEDUPLICATION_TTL_SECONDS: int = 15

    # Background Tasks & Cache
    REDIS_URL: str | None = None

    # Limits
    MAX_UPLOAD_BYTES: int = 52428800  # 50 MB
    MAX_DOCUMENT_PAGES: int = 500

    # Local Storage Directory
    UPLOAD_DIR: Path = Path("uploads")


settings = Settings()
