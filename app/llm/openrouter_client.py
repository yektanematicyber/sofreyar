import asyncio
import json
import logging
import time
from typing import Any

import httpx
from pydantic import ValidationError

from app.llm.config import LLMConfig, get_llm_config
from app.llm.interface import (
    LLMAuthenticationError,
    LLMInvalidResponse,
    LLMProviderError,
    LLMRateLimitError,
    LLMService,
    LLMTimeout,
    MealType,
    PantryItemInput,
    Recipe,
)
from app.llm.prompts import SYSTEM_PROMPT, build_retry_prompt, build_user_prompt
from app.llm.telemetry import log_llm_telemetry

logger = logging.getLogger("safreyar.llm.openrouter")


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


class OpenRouterLLMService(LLMService):
    """Production LLM Service implementation using OpenRouter's OpenAI-compatible Chat Completions API."""

    def __init__(
        self,
        config: LLMConfig | None = None,
        client: httpx.AsyncClient | None = None,
    ):
        self.config = config or get_llm_config()
        self._custom_client = client is not None
        self._client = client or httpx.AsyncClient(
            timeout=httpx.Timeout(self.config.llm_timeout_seconds, connect=10.0),
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
        )

    async def close(self) -> None:
        """Closes the underlying httpx.AsyncClient if managed internally."""
        if not self._custom_client and self._client and not self._client.is_closed:
            await self._client.aclose()

    async def __aenter__(self) -> "OpenRouterLLMService":
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()

    async def _call_model(
        self,
        prompt: str,
        attempt: int,
        user_id: int | None = None,
        request_id: str | None = None,
    ) -> tuple[str, int, int, float]:
        """Calls OpenRouter Chat Completions endpoint with timeout mapping, error categorization, and latency tracking."""
        base_url = self.config.llm_base_url.rstrip("/")
        url = f"{base_url}/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.config.llm_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/yektanematicyber/sofreyar",
            "X-Title": "Safreyar",
        }

        payload = {
            "model": self.config.llm_model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.7,
            "max_tokens": 4096,
        }

        start_time = time.monotonic()
        try:
            response = await self._client.post(
                url,
                headers=headers,
                json=payload,
            )
        except (httpx.TimeoutException, asyncio.TimeoutError) as err:
            latency_ms = round((time.monotonic() - start_time) * 1000, 2)
            logger.warning(
                "OpenRouter request timed out | model=%s attempt=%d timeout_s=%.1f",
                self.config.llm_model,
                attempt,
                self.config.llm_timeout_seconds,
            )
            log_llm_telemetry(
                user_id=user_id,
                request_id=request_id,
                model_name=self.config.llm_model,
                input_tokens=0,
                output_tokens=0,
                latency_ms=latency_ms,
                status="timeout",
            )
            raise LLMTimeout(
                f"OpenRouter request timed out after {self.config.llm_timeout_seconds} seconds"
            ) from err
        except httpx.RequestError as err:
            latency_ms = round((time.monotonic() - start_time) * 1000, 2)
            logger.error("OpenRouter network connection error: %s", err)
            log_llm_telemetry(
                user_id=user_id,
                request_id=request_id,
                model_name=self.config.llm_model,
                input_tokens=0,
                output_tokens=0,
                latency_ms=latency_ms,
                status="provider_error",
            )
            raise LLMProviderError(f"OpenRouter network connection failed: {err}") from err

        latency_ms = round((time.monotonic() - start_time) * 1000, 2)

        # Categorize HTTP status codes
        if response.status_code in (401, 403):
            logger.error("OpenRouter authentication error (status %d)", response.status_code)
            log_llm_telemetry(
                user_id=user_id,
                request_id=request_id,
                model_name=self.config.llm_model,
                input_tokens=0,
                output_tokens=0,
                latency_ms=latency_ms,
                status="provider_error",
            )
            raise LLMAuthenticationError(
                f"OpenRouter authentication failed with status {response.status_code}"
            )
        elif response.status_code == 429:
            logger.warning("OpenRouter rate limit or credit quota reached (status 429)")
            log_llm_telemetry(
                user_id=user_id,
                request_id=request_id,
                model_name=self.config.llm_model,
                input_tokens=0,
                output_tokens=0,
                latency_ms=latency_ms,
                status="provider_error",
            )
            raise LLMRateLimitError("OpenRouter rate limit or credit quota exceeded.")
        elif response.is_error:
            logger.error("OpenRouter returned error HTTP status %d: %s", response.status_code, response.text[:200])
            log_llm_telemetry(
                user_id=user_id,
                request_id=request_id,
                model_name=self.config.llm_model,
                input_tokens=0,
                output_tokens=0,
                latency_ms=latency_ms,
                status="provider_error",
            )
            raise LLMProviderError(f"OpenRouter returned HTTP {response.status_code}")

        # Validate OpenRouter JSON payload structure
        try:
            data = response.json()
        except Exception as err:
            logger.error("Failed to decode OpenRouter JSON response: %s", err)
            raise LLMInvalidResponse(f"OpenRouter response is not valid JSON: {err}") from err

        if not isinstance(data, dict):
            raise LLMInvalidResponse("OpenRouter response body is not a JSON object.")

        if "error" in data:
            err_data = data["error"]
            err_msg = err_data.get("message", str(err_data)) if isinstance(err_data, dict) else str(err_data)
            raise LLMProviderError(f"OpenRouter API error: {err_msg}")

        choices = data.get("choices")
        if not choices or not isinstance(choices, list):
            raise LLMInvalidResponse("OpenRouter response contains missing or empty choices.")

        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            raise LLMInvalidResponse("OpenRouter choice item is not a valid JSON object.")

        message = first_choice.get("message", {})
        raw_text = message.get("content", "")
        if not raw_text or not raw_text.strip():
            raise LLMInvalidResponse("OpenRouter choice returned empty content.")

        usage = data.get("usage", {})
        input_tokens = usage.get("prompt_tokens", 0) if isinstance(usage, dict) else 0
        output_tokens = usage.get("completion_tokens", 0) if isinstance(usage, dict) else 0

        logger.info(
            "OpenRouter call completed | model=%s latency_ms=%.2f in_tokens=%d out_tokens=%d attempt=%d",
            self.config.llm_model,
            latency_ms,
            input_tokens,
            output_tokens,
            attempt,
        )

        return raw_text, input_tokens, output_tokens, latency_ms

    async def generate_recipes(
        self,
        pantry_items: list[PantryItemInput],
        meal_type: MealType,
        servings: int,
        user_id: int | None = None,
        request_id: str | None = None,
        **kwargs: Any,
    ) -> list[Recipe]:
        """Generates exactly 3 recipes from pantry items with one-shot retry validation."""
        initial_prompt = build_user_prompt(pantry_items, meal_type, servings)

        # Attempt 1
        raw_text, in_tok1, out_tok1, lat1 = await self._call_model(
            initial_prompt, attempt=1, user_id=user_id, request_id=request_id
        )
        first_error_msg = ""
        try:
            recipes = _parse_and_validate_recipes(raw_text)
            log_llm_telemetry(
                user_id=user_id,
                request_id=request_id,
                model_name=self.config.llm_model,
                input_tokens=in_tok1,
                output_tokens=out_tok1,
                latency_ms=lat1,
                status="success",
                retry_required=False,
                from_cache=False,
                is_fake=False,
            )
            return recipes
        except ValueError as first_err:
            first_error_msg = str(first_err)
            logger.warning(
                "First OpenRouter response validation failed; triggering one-shot retry. Reason: %s",
                first_err,
            )

        # Attempt 2 (One-shot retry with error explanation in prompt)
        retry_prompt = build_retry_prompt(initial_prompt, raw_text, first_error_msg)
        raw_retry_text, in_tok2, out_tok2, lat2 = await self._call_model(
            retry_prompt, attempt=2, user_id=user_id, request_id=request_id
        )
        total_in = in_tok1 + in_tok2
        total_out = out_tok1 + out_tok2
        total_lat = lat1 + lat2
        try:
            recipes = _parse_and_validate_recipes(raw_retry_text)
            log_llm_telemetry(
                user_id=user_id,
                request_id=request_id,
                model_name=self.config.llm_model,
                input_tokens=total_in,
                output_tokens=total_out,
                latency_ms=total_lat,
                status="success",
                retry_required=True,
                from_cache=False,
                is_fake=False,
            )
            return recipes
        except ValueError as second_err:
            log_llm_telemetry(
                user_id=user_id,
                request_id=request_id,
                model_name=self.config.llm_model,
                input_tokens=total_in,
                output_tokens=total_out,
                latency_ms=total_lat,
                status="failed",
                retry_required=True,
                from_cache=False,
                is_fake=False,
            )
            logger.error(
                "Second OpenRouter response validation failed after retry. Reason: %s",
                second_err,
            )
            raise LLMInvalidResponse(
                f"OpenRouter generated invalid response after retry: {second_err}"
            ) from second_err
