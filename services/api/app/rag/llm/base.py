from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
from app.core.errors import AppError


class LLMError(AppError):
    """Raised when an LLM provider fails to generate a response."""
    def __init__(self, message: str, details: dict | None = None):
        super().__init__(
            status_code=502,
            code="LLM_PROVIDER_ERROR",
            message=message,
            details=details,
        )


@dataclass
class LLMResponse:
    """Standardized response from an LLM provider."""
    content: str
    latency_ms: int
    model: str
    provider: str
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None


class BaseLLMProvider(ABC):
    """Abstract base class for LLM generation providers."""

    def __init__(self, provider_name: str, model_id: str):
        self.provider_name = provider_name
        self.model_id = model_id

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
    ) -> LLMResponse:
        """Generate text completion for a given prompt."""
        pass
