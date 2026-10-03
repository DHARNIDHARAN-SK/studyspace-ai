from app.core.config import settings
from app.rag.embeddings.base import BaseEmbeddingProvider, EmbeddingError
from app.rag.embeddings.ollama_provider import OllamaEmbeddingProvider


def get_embedding_provider() -> BaseEmbeddingProvider:
    """
    Factory resolving the active embedding provider according to application configuration.
    For local development and testing through Phase 11, strictly resolves Ollama.
    """
    provider_name = settings.EMBEDDING_PROVIDER.lower()
    if provider_name == "ollama":
        return OllamaEmbeddingProvider(
            base_url=settings.OLLAMA_BASE_URL,
            model_id=settings.EMBEDDING_MODEL_ID,
            dimension=settings.EMBEDDING_VECTOR_DIMENSIONS,
        )
    else:
        raise EmbeddingError(
            f"Unsupported embedding provider: '{provider_name}'. Local development requires 'ollama'."
        )
