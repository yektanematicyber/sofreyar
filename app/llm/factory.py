import os
from app.llm.fake import FakeLLMService
from app.llm.interface import LLMService


def get_llm_service() -> LLMService:
    """Factory function returning the appropriate LLMService instance.

    Controlled by the LLM_MODE environment variable:
      - 'fake' (default): returns FakeLLMService for deterministic offline use.
      - 'real': returns AnthropicLLMService connected to Claude API.
    """
    mode = os.getenv("LLM_MODE", "fake").strip().lower()

    if mode == "real":
        try:
            from app.llm.client import AnthropicLLMService

            return AnthropicLLMService()
        except ImportError:
            raise RuntimeError(
                "AnthropicLLMService requested via LLM_MODE=real, but app.llm.client could not be loaded."
            )

    return FakeLLMService()
