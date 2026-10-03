from typing import Optional

from app.core.config import settings
from app.core.errors import AppError
from app.core.logging import logger
from app.rag.reranking.base import BaseReranker
from app.rag.reranking.local_cross_encoder import LocalCrossEncoderReranker
from app.rag.reranking.passthrough import PassthroughReranker


class RerankerModelNotFoundError(AppError):
    def __init__(self, message: str):
        super().__init__(message=message, code="RERANKER_MODEL_NOT_FOUND", status_code=500)


def get_reranker(provider: Optional[str] = None) -> BaseReranker:
    """
    Factory function returning the configured Reranker provider.
    Enforces strict safety: will NOT silently pull external models or packages.
    """
    prov = (provider or settings.RERANKER_PROVIDER or "disabled").strip().lower()

    if prov == "disabled":
        logger.info("Reranker is disabled: using PassthroughReranker.")
        return PassthroughReranker()

    if prov == "local":
        logger.info("Using LocalCrossEncoderReranker (zero-dependency, deterministic local cross-scorer).")
        return LocalCrossEncoderReranker()

    if prov in ("sentence_transformers", "cross_encoder", "flashrank"):
        # Check if requested external neural model library is installed
        try:
            if prov == "flashrank":
                import flashrank  # noqa: F401
            else:
                import sentence_transformers  # noqa: F401
        except ImportError as exc:
            msg = (
                f"Requested neural reranker provider '{prov}' requires an external library that is not installed. "
                "Per system constraints, external models/libraries will not be pulled silently without explicit request."
            )
            logger.error(msg)
            raise RerankerModelNotFoundError(msg) from exc

    logger.warning("Unknown reranker provider '%s'; defaulting to LocalCrossEncoderReranker.", prov)
    return LocalCrossEncoderReranker()
