from app.core.config import settings
from app.rag.llm.base import BaseLLMProvider, LLMError
from app.rag.llm.ollama_provider import OllamaLLMProvider


def get_llm_provider() -> BaseLLMProvider:
    """
    Factory resolving the active LLM provider.
    For local development through Phase 11, strictly resolves Ollama with phi4-mini:latest.
    """
    provider_name = settings.LLM_PROVIDER.lower()
    if provider_name == "ollama":
        return OllamaLLMProvider(
            base_url=settings.OLLAMA_BASE_URL,
            model_id=settings.OLLAMA_CHAT_MODEL,
        )
    else:
        raise LLMError(
            f"Unsupported LLM provider: '{provider_name}'. Local development strictly requires 'ollama'."
        )
