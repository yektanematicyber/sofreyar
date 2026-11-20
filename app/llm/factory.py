from app.llm.config import get_llm_config
from app.llm.fake import FakeLLMService
from app.llm.interface import LLMService


def get_llm_service() -> LLMService:
    """Factory function returning the appropriate LLMService instance.

    Controlled by LLMConfig (reads .env / environment variables):
      - 'fake' (default): returns FakeLLMService for deterministic offline use.
      - 'real': returns AnthropicLLMService connected to Claude API.
    """
    config = get_llm_config()
    mode = config.llm_mode.strip().lower()

    if mode == "real":
        try:
            from app.llm.client import AnthropicLLMService

            return AnthropicLLMService(config=config)
        except ImportError as err:
            raise RuntimeError(
                "AnthropicLLMService requested via LLM_MODE=real, but app.llm.client could not be loaded."
            ) from err

    return FakeLLMService()
