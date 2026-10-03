import time
from typing import Optional
import httpx

from app.core.config import settings
from app.core.logging import logger
from app.rag.llm.base import BaseLLMProvider, LLMError, LLMResponse


class OllamaLLMProvider(BaseLLMProvider):
    """
    Ollama LLM generation provider utilizing phi4-mini:latest for baseline RAG.
    Connects to local Ollama daemon without external cloud dependencies.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model_id: Optional[str] = None,
        timeout: float = 90.0,
    ):
        model = model_id or settings.OLLAMA_CHAT_MODEL
        super().__init__(provider_name="ollama", model_id=model)
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.timeout = timeout

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
    ) -> LLMResponse:
        """
        Executes text generation using phi4-mini via Ollama /api/generate.
        """
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model_id,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
            },
        }
        if system_prompt:
            payload["system"] = system_prompt

        start_time = time.time()
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()

            latency_ms = int((time.time() - start_time) * 1000)
            content = data.get("response", "").strip()

            prompt_tokens = data.get("prompt_eval_count")
            completion_tokens = data.get("eval_count")

            logger.info(
                "Ollama generated response (%d chars, latency=%dms, model=%s)",
                len(content),
                latency_ms,
                self.model_id,
            )

            return LLMResponse(
                content=content,
                latency_ms=latency_ms,
                model=self.model_id,
                provider=self.provider_name,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
            )

        except httpx.HTTPError as exc:
            logger.error("Ollama LLM HTTP error: %s", exc)
            raise LLMError(f"Failed to communicate with Ollama generation service: {exc}")
        except Exception as exc:
            if isinstance(exc, LLMError):
                raise
            logger.error("Ollama LLM unexpected error: %s", exc)
            raise LLMError(f"Unexpected error in LLM generation: {exc}")
