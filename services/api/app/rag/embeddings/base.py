from abc import ABC, abstractmethod
from typing import List
from app.core.errors import AppError


class EmbeddingError(AppError):
    """Raised when an embedding provider fails to compute vectors."""
    def __init__(self, message: str, details: dict | None = None):
        super().__init__(
            status_code=502,
            code="EMBEDDING_PROVIDER_ERROR",
            message=message,
            details=details,
        )


class DimensionMismatchError(AppError):
    """Raised when generated embedding dimension does not match database schema."""
    def __init__(self, expected: int, received: int):
        super().__init__(
            status_code=500,
            code="EMBEDDING_DIMENSION_MISMATCH",
            message=(
                f"Embedding dimension mismatch: expected {expected} dimensions "
                f"but provider produced {received} dimensions."
            ),
            details={"expected": expected, "received": received},
        )


class BaseEmbeddingProvider(ABC):
    """Abstract base class for vector embedding providers."""

    def __init__(self, provider_name: str, model_id: str, dimension: int = 768):
        self.provider_name = provider_name
        self.model_id = model_id
        self.dimension = dimension

    def validate_dimension(self, embedding: List[float]) -> None:
        """Validates that a generated embedding vector matches the required dimension."""
        if len(embedding) != self.dimension:
            raise DimensionMismatchError(expected=self.dimension, received=len(embedding))

    @abstractmethod
    async def embed_text(self, text: str) -> List[float]:
        """Generate an embedding vector for a single string."""
        pass

    @abstractmethod
    async def embed_batch(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """Generate embedding vectors for a list of strings in batches."""
        pass
