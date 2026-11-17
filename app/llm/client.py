import asyncio
import json
import logging
import time
from typing import Any

from pydantic import ValidationError

from app.llm.config import LLMConfig, get_llm_config
from app.llm.interface import (
    LLMInvalidResponse,
    LLMService,
    LLMTimeout,
    MealType,
    PantryItemInput,
    Recipe,
)
from app.llm.prompts import SYSTEM_PROMPT, build_retry_prompt, build_user_prompt

logger = logging.getLogger("safreyar.llm")


def _clean_json_text(raw_text: str) -> str:
    """Strips possible markdown code fence blocks from the raw model response."""
    text = raw_text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def _parse_and_validate_recipes(raw_text: str) -> list[Recipe]:
    """Parses JSON text and strictly validates that exactly 3 recipes are returned."""
    cleaned = _clean_json_text(raw_text)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as err:
        raise ValueError(f"Malformed JSON: {err}") from err

    # Support list or dict wrapped format {"recipes": [...]}
    if isinstance(data, dict):
        if "recipes" in data and isinstance(data["recipes"], list):
            data = data["recipes"]
        else:
            raise ValueError("Expected a JSON array of recipes or {'recipes': [...]}")

    if not isinstance(data, list):
        raise ValueError(f"Expected a JSON list, got {type(data).__name__}")

    if len(data) != 3:
        raise ValueError(
            f"Expected exactly 3 recipes, but received {len(data)} recipes."
        )

    recipes: list[Recipe] = []
    for idx, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Recipe #{idx} is not a valid JSON object.")
        try:
            recipes.append(Recipe.model_validate(item))
        except ValidationError as err:
            raise ValueError(f"Validation error in recipe #{idx}: {err}") from err

    return recipes


class AnthropicLLMService(LLMService):
    """Production LLM Service implementation using the official Anthropic Claude SDK."""

    def __init__(
        self,
        client: Any | None = None,
        config: LLMConfig | None = None,
    ):
        self.config = config or get_llm_config()
        if client is not None:
            self._client = client
        else:
            import anthropic

            self._client = anthropic.AsyncAnthropic(
                api_key=self.config.llm_api_key or None,
                timeout=self.config.llm_timeout_seconds,
            )

    async def _call_model(self, prompt: str, attempt: int) -> tuple[str, int, int, float]:
        """Calls the Anthropic Messages API, tracks latency and token usage, and converts timeouts."""
        import anthropic

        start_time = time.monotonic()
        try:
            response = await asyncio.wait_for(
                self._client.messages.create(
                    model=self.config.llm_model,
                    max_tokens=4096,
                    temperature=0.7,
                    system=SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": prompt}],
                ),
                timeout=self.config.llm_timeout_seconds,
            )
        except (anthropic.APITimeoutError, asyncio.TimeoutError) as err:
            logger.warning(
                "LLM request timed out | model=%s attempt=%d timeout_s=%.1f",
                self.config.llm_model,
                attempt,
                self.config.llm_timeout_seconds,
            )
            raise LLMTimeout(
                f"LLM request timed out after {self.config.llm_timeout_seconds} seconds"
            ) from err

        latency_ms = round((time.monotonic() - start_time) * 1000, 2)
        input_tokens = (
            response.usage.input_tokens
            if hasattr(response, "usage") and response.usage
            else 0
        )
        output_tokens = (
            response.usage.output_tokens
            if hasattr(response, "usage") and response.usage
            else 0
        )

        logger.info(
            "LLM call completed | model=%s latency_ms=%.2f input_tokens=%d output_tokens=%d attempt=%d",
            self.config.llm_model,
            latency_ms,
            input_tokens,
            output_tokens,
            attempt,
        )

        # Extract text content from message blocks
        raw_text = ""
        if response.content:
            for block in response.content:
                if hasattr(block, "text"):
                    raw_text += block.text

        return raw_text, input_tokens, output_tokens, latency_ms

    async def generate_recipes(
        self,
        pantry_items: list[PantryItemInput],
        meal_type: MealType,
        servings: int,
    ) -> list[Recipe]:
        """Generates exactly 3 recipes from pantry items with one-shot retry validation."""
        initial_prompt = build_user_prompt(pantry_items, meal_type, servings)

        # Attempt 1
        raw_text, _, _, _ = await self._call_model(initial_prompt, attempt=1)
        first_error_msg = ""
        try:
            return _parse_and_validate_recipes(raw_text)
        except ValueError as first_err:
            first_error_msg = str(first_err)
            logger.warning(
                "First LLM response validation failed; triggering one-shot retry. Reason: %s",
                first_err,
            )

        # Attempt 2 (One-shot retry with error in prompt)
        retry_prompt = build_retry_prompt(initial_prompt, raw_text, first_error_msg)
        raw_retry_text, _, _, _ = await self._call_model(retry_prompt, attempt=2)
        try:
            return _parse_and_validate_recipes(raw_retry_text)
        except ValueError as second_err:
            logger.error(
                "Second LLM response validation failed after retry. Reason: %s",
                second_err,
            )
            raise LLMInvalidResponse(
                f"LLM generated invalid response after retry: {second_err}"
            ) from second_err
