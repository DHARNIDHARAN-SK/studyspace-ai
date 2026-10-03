import time
from typing import List, Optional
import httpx

from app.core.config import settings
from app.core.logging import logger
from app.rag.embeddings.base import BaseEmbeddingProvider, EmbeddingError


class OllamaEmbeddingProvider(BaseEmbeddingProvider):
    """
    Ollama-based embedding provider utilizing nomic-embed-text:latest (768 dimensions).
    Supports single-text and batch embedding via Ollama's HTTP API.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model_id: Optional[str] = None,
        dimension: Optional[int] = None,
        timeout: float = 60.0,
    ):
        provider_name = "ollama"
        model = model_id or settings.EMBEDDING_MODEL_ID
        dim = dimension or settings.EMBEDDING_VECTOR_DIMENSIONS
        super().__init__(provider_name=provider_name, model_id=model, dimension=dim)
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.timeout = timeout

    async def embed_text(self, text: str) -> List[float]:
        """Embeds a single text using nomic-embed-text."""
        if not text or not text.strip():
            # Return zero vector or placeholder if text is completely empty
            return [0.0] * self.dimension

        url = f"{self.base_url}/api/embed"
        payload = {"model": self.model_id, "input": text.strip()}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code == 404:
                    # Fallback to legacy /api/embeddings endpoint
                    return await self._embed_text_legacy(text)

                resp.raise_for_status()
                data = resp.json()

                embeddings = data.get("embeddings", [])
                if not embeddings:
                    raise EmbeddingError(f"Ollama returned no embeddings for text using model {self.model_id}")

                embedding = embeddings[0]
                self.validate_dimension(embedding)
                return embedding

        except httpx.HTTPError as exc:
            logger.error("Ollama embedding HTTP error: %s", exc)
            raise EmbeddingError(f"Failed to communicate with Ollama embedding service: {exc}")
        except Exception as exc:
            if isinstance(exc, EmbeddingError):
                raise
            logger.error("Ollama embedding unexpected error: %s", exc)
            raise EmbeddingError(f"Unexpected error generating embeddings: {exc}")

    async def _embed_text_legacy(self, text: str) -> List[float]:
        """Fallback for older Ollama versions using /api/embeddings."""
        url = f"{self.base_url}/api/embeddings"
        payload = {"model": self.model_id, "prompt": text.strip()}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            embedding = data.get("embedding", [])
            self.validate_dimension(embedding)
            return embedding

    async def embed_batch(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """
        Embeds a list of strings in chunks to prevent timeout or oversized payloads.
        Returns a list of 768-dimensional float vectors matching the input text order.
        """
        if not texts:
            return []

        all_embeddings: List[List[float]] = []
        clean_texts = [t.strip() if t and t.strip() else " " for t in texts]

        url = f"{self.base_url}/api/embed"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for i in range(0, len(clean_texts), batch_size):
                batch = clean_texts[i : i + batch_size]
                payload = {"model": self.model_id, "input": batch}

                start_t = time.time()
                try:
                    resp = await client.post(url, json=payload)
                    if resp.status_code == 404:
                        # Fallback to sequential legacy calls if /api/embed not available
                        for single_t in batch:
                            emb = await self._embed_text_legacy(single_t)
                            all_embeddings.append(emb)
                        continue

                    resp.raise_for_status()
                    data = resp.json()
                    batch_embeddings = data.get("embeddings", [])

                    if len(batch_embeddings) != len(batch):
                        raise EmbeddingError(
                            f"Mismatch in returned embeddings count: expected {len(batch)}, got {len(batch_embeddings)}"
                        )

                    for emb in batch_embeddings:
                        self.validate_dimension(emb)
                        all_embeddings.append(emb)

                    logger.debug(
                        "Embedded batch [%d-%d/%d] in %.2fs",
                        i,
                        i + len(batch),
                        len(clean_texts),
                        time.time() - start_t,
                    )

                except httpx.HTTPError as exc:
                    logger.error("Ollama batch embedding failed at slice [%d:%d]: %s", i, i + len(batch), exc)
                    raise EmbeddingError(f"Ollama batch embedding failed: {exc}")

        return all_embeddings
