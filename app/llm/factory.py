from app.llm.config import get_llm_config
from app.llm.fake import FakeLLMService
from app.llm.interface import LLMService

_service_instance: LLMService | None = None


def get_llm_service() -> LLMService:
    """Factory function returning the appropriate LLMService instance.

    Controlled by LLMConfig (reads .env / environment variables):
      - 'fake' (default): returns FakeLLMService for deterministic offline use.
      - 'real': returns OpenRouterLLMService connected to OpenRouter API.
    """
    global _service_instance
    if _service_instance is not None:
        return _service_instance

    config = get_llm_config()
    mode = config.llm_mode.strip().lower()

    if mode == "real":
        try:
            from app.llm.openrouter_client import OpenRouterLLMService

            _service_instance = OpenRouterLLMService(config=config)
            return _service_instance
        except ImportError as err:
            raise RuntimeError(
                "OpenRouterLLMService requested via LLM_MODE=real, but app.llm.openrouter_client could not be loaded."
            ) from err

    _service_instance = FakeLLMService()
    return _service_instance


async def close_llm_service() -> None:
    """Closes any open resources (like httpx connection pools) on application shutdown."""
    global _service_instance
    if _service_instance is not None:
        if hasattr(_service_instance, "close"):
            await _service_instance.close()
        _service_instance = None


def reset_llm_service() -> None:
    """Resets cached service instance (primarily used in tests)."""
    global _service_instance
    _service_instance = None
