import asyncio
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from pydantic import ValidationError

from app.llm.config import LLMConfig
from app.llm.interface import (
    LLMAuthenticationError,
    LLMInvalidResponse,
    LLMProviderError,
    LLMRateLimitError,
    LLMTimeout,
    Nutrition,
    PantryItemInput,
    Recipe,
    RecipeIngredient,
)
from app.llm.openrouter_client import (
    OpenRouterLLMService,
    _clean_json_text,
    _parse_and_validate_recipes,
)
from app.llm.prompts import build_user_prompt

SAMPLE_VALID_RECIPES_JSON = """[
  {
    "title": "املت گوجه‌فرنگی",
    "summary": "یک صبحانه لذیذ و پرطرفدار ایرانی.",
    "emoji": "🍳",
    "time_minutes": 15,
    "difficulty": "easy",
    "servings": 2,
    "ingredients": [
      {"name": "تخم‌مرغ", "amount": 4.0, "unit": "piece", "in_pantry": true},
      {"name": "گوجه‌فرنگی", "amount": 3.0, "unit": "piece", "in_pantry": false}
    ],
    "uses": ["تخم‌مرغ"],
    "missing": ["گوجه‌فرنگی"],
    "steps": ["گوجه را رنده کنید.", "تخم‌مرغ را اضافه کنید."],
    "nutrition": {
      "calories": 250,
      "protein_g": 14.0,
      "fiber_g": 2.0,
      "carbs_g": 8.0,
      "fat_g": 18.0
    }
  },
  {
    "title": "کوکو سبزی",
    "summary": "کوکوی لذیذ و پر از سبزیجات معطر.",
    "emoji": "🌿",
    "time_minutes": 25,
    "difficulty": "medium",
    "servings": 2,
    "ingredients": [
      {"name": "سبزی کوکو", "amount": 200.0, "unit": "g", "in_pantry": true},
      {"name": "تخم‌مرغ", "amount": 3.0, "unit": "piece", "in_pantry": true},
      {"name": "روغن", "amount": 20.0, "unit": "ml", "in_pantry": false}
    ],
    "uses": ["سبزی کوکو", "تخم‌مرغ"],
    "missing": ["روغن"],
    "steps": ["سبزی را با تخم‌مرغ مخلوط کنید.", "در تابه سرخ کنید."],
    "nutrition": {
      "calories": 280,
      "protein_g": 12.0,
      "fiber_g": 4.0,
      "carbs_g": 6.0,
      "fat_g": 22.0
    }
  },
  {
    "title": "ماست و خیار مجلسی",
    "summary": "پیش‌غذای خنک و ساده ایرانی.",
    "emoji": "🥣",
    "time_minutes": 10,
    "difficulty": "easy",
    "servings": 2,
    "ingredients": [
      {"name": "ماست", "amount": 400.0, "unit": "g", "in_pantry": true},
      {"name": "خیار", "amount": 2.0, "unit": "piece", "in_pantry": false}
    ],
    "uses": ["ماست"],
    "missing": ["خیار"],
    "steps": ["خیار را رنده کنید.", "با ماست مخلوط نمایید."],
    "nutrition": {
      "calories": 150,
      "protein_g": 8.0,
      "fiber_g": 1.0,
      "carbs_g": 12.0,
      "fat_g": 6.0
    }
  }
]"""


def make_mock_openrouter_response(
    content_text: str,
    status_code: int = 200,
    prompt_tokens: int = 150,
    completion_tokens: int = 400,
    extra_json: dict | None = None,
) -> httpx.Response:
    if extra_json is not None:
        payload = extra_json
    else:
        payload = {
            "id": "gen-test-12345",
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": content_text,
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            },
        }

    return httpx.Response(
        status_code=status_code,
        json=payload,
        request=httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions"),
    )


def test_clean_json_text():
    raw_markdown = f"```json\n{SAMPLE_VALID_RECIPES_JSON}\n```"
    assert _clean_json_text(raw_markdown) == SAMPLE_VALID_RECIPES_JSON


def test_parse_and_validate_recipes_success():
    recipes = _parse_and_validate_recipes(SAMPLE_VALID_RECIPES_JSON)
    assert len(recipes) == 3
    assert recipes[0].title == "املت گوجه‌فرنگی"
    assert recipes[0].time_minutes == 15
    assert recipes[0].difficulty == "easy"
    assert recipes[0].servings == 2


def test_parse_and_validate_recipes_wrong_count():
    two_recipes = """[
      {
        "title": "املت",
        "summary": "توضیح",
        "emoji": "🍳",
        "time_minutes": 15,
        "difficulty": "easy",
        "servings": 2,
        "ingredients": [],
        "uses": [],
        "missing": [],
        "steps": ["پخت"],
        "nutrition": {"calories": 100, "protein_g": 5, "fiber_g": 1, "carbs_g": 5, "fat_g": 5}
      },
      {
        "title": "کوکو",
        "summary": "توضیح",
        "emoji": "🌿",
        "time_minutes": 20,
        "difficulty": "easy",
        "servings": 2,
        "ingredients": [],
        "uses": [],
        "missing": [],
        "steps": ["پخت"],
        "nutrition": {"calories": 100, "protein_g": 5, "fiber_g": 1, "carbs_g": 5, "fat_g": 5}
      }
    ]"""
    with pytest.raises(ValueError, match="Expected exactly 3 recipes, but received 2 recipes"):
        _parse_and_validate_recipes(two_recipes)


def test_build_user_prompt_prioritizes_expiry():
    today = date.today()
    items = [
        PantryItemInput(name="شیر", quantity=1.0, unit="l", expiry_date=today + timedelta(days=10)),
        PantryItemInput(name="ماست", quantity=500.0, unit="g", expiry_date=today + timedelta(days=1)),
        PantryItemInput(name="برنج", quantity=2.0, unit="kg", expiry_date=None),
        PantryItemInput(name="پنیر", quantity=200.0, unit="g", expiry_date=today),
    ]

    prompt = build_user_prompt(items, meal_type="breakfast", servings=2)

    pos_panir = prompt.index("پنیر")
    pos_mast = prompt.index("ماست")
    pos_shir = prompt.index("شیر")
    pos_berenj = prompt.index("برنج")

    assert pos_panir < pos_mast < pos_shir < pos_berenj


def test_build_user_prompt_flags_expired_items_as_unsafe():
    today = date.today()
    items = [
        PantryItemInput(
            name="شیر فاسد",
            quantity=1.0,
            unit="l",
            expiry_date=today - timedelta(days=2),
        ),
        PantryItemInput(
            name="ماست تازه",
            quantity=500.0,
            unit="g",
            expiry_date=today + timedelta(days=2),
        ),
    ]

    prompt = build_user_prompt(items, meal_type="breakfast", servings=2)

    assert "منقضی شده و غیرقابل مصرف" in prompt
    assert "خطر سلامتی" in prompt
    assert "سالم، اولویت بالا" in prompt
    assert "هرگز از اقلام منقضی‌شده و فاسد استفاده نکنید" in prompt


@pytest.mark.anyio
async def test_openrouter_valid_json_success():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post.return_value = make_mock_openrouter_response(SAMPLE_VALID_RECIPES_JSON)

    config = LLMConfig(
        llm_api_key="sk-or-v1-test",
        llm_model="google/gemma-4-26b-a4b-it:free",
        llm_timeout_seconds=5.0,
    )
    service = OpenRouterLLMService(config=config, client=mock_client)

    items = [PantryItemInput(name="تخم‌مرغ", quantity=4.0, unit="piece")]
    recipes = await service.generate_recipes(items, "dinner", 2)

    assert len(recipes) == 3
    assert recipes[0].title == "املت گوجه‌فرنگی"
    assert mock_client.post.await_count == 1


@pytest.mark.anyio
async def test_openrouter_malformed_json_retry_succeeds():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    # 1st attempt: malformed JSON, 2nd attempt: valid JSON
    mock_client.post.side_effect = [
        make_mock_openrouter_response("{invalid json...}"),
        make_mock_openrouter_response(SAMPLE_VALID_RECIPES_JSON),
    ]

    config = LLMConfig(llm_api_key="sk-or-v1-test", llm_timeout_seconds=5.0)
    service = OpenRouterLLMService(config=config, client=mock_client)

    items = [PantryItemInput(name="سبزی", quantity=1.0, unit="kg")]
    recipes = await service.generate_recipes(items, "lunch", 2)

    assert len(recipes) == 3
    assert mock_client.post.await_count == 2


@pytest.mark.anyio
async def test_openrouter_two_failures_raises_llm_invalid_response():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post.side_effect = [
        make_mock_openrouter_response("Not JSON at all"),
        make_mock_openrouter_response("Still not JSON"),
    ]

    config = LLMConfig(llm_api_key="sk-or-v1-test", llm_timeout_seconds=5.0)
    service = OpenRouterLLMService(config=config, client=mock_client)

    items = [PantryItemInput(name="ماست", quantity=500.0, unit="g")]
    with pytest.raises(LLMInvalidResponse, match="invalid response after retry"):
        await service.generate_recipes(items, "snack", 1)

    assert mock_client.post.await_count == 2


@pytest.mark.anyio
async def test_openrouter_timeout_raises_llm_timeout():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post.side_effect = httpx.ReadTimeout("Connection timed out")

    config = LLMConfig(llm_api_key="sk-or-v1-test", llm_timeout_seconds=2.0)
    service = OpenRouterLLMService(config=config, client=mock_client)

    items = [PantryItemInput(name="شیر", quantity=1.0, unit="l")]
    with pytest.raises(LLMTimeout, match="timed out"):
        await service.generate_recipes(items, "breakfast", 2)


@pytest.mark.anyio
async def test_openrouter_auth_error_raises_llm_auth_error():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post.return_value = httpx.Response(
        status_code=401,
        text='{"error": "Unauthorized"}',
        request=httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions"),
    )

    config = LLMConfig(llm_api_key="invalid-key")
    service = OpenRouterLLMService(config=config, client=mock_client)

    items = [PantryItemInput(name="نان", quantity=1.0, unit="piece")]
    with pytest.raises(LLMAuthenticationError):
        await service.generate_recipes(items, "breakfast", 1)


@pytest.mark.anyio
async def test_openrouter_rate_limit_raises_llm_rate_limit_error():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post.return_value = httpx.Response(
        status_code=429,
        text='{"error": "Rate limit exceeded"}',
        request=httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions"),
    )

    config = LLMConfig(llm_api_key="test-key")
    service = OpenRouterLLMService(config=config, client=mock_client)

    items = [PantryItemInput(name="نان", quantity=1.0, unit="piece")]
    with pytest.raises(LLMRateLimitError):
        await service.generate_recipes(items, "breakfast", 1)


@pytest.mark.anyio
async def test_openrouter_provider_error_payload_handling():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post.return_value = httpx.Response(
        status_code=500,
        text="Internal Server Error",
        request=httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions"),
    )

    config = LLMConfig(llm_api_key="test-key")
    service = OpenRouterLLMService(config=config, client=mock_client)

    items = [PantryItemInput(name="نان", quantity=1.0, unit="piece")]
    with pytest.raises(LLMProviderError):
        await service.generate_recipes(items, "breakfast", 1)


@pytest.mark.anyio
async def test_openrouter_empty_choices_raises_invalid_response():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post.return_value = make_mock_openrouter_response("", extra_json={"id": "test", "choices": []})

    config = LLMConfig(llm_api_key="test-key")
    service = OpenRouterLLMService(config=config, client=mock_client)

    items = [PantryItemInput(name="نان", quantity=1.0, unit="piece")]
    with pytest.raises(LLMInvalidResponse, match="missing or empty choices"):
        await service.generate_recipes(items, "breakfast", 1)


@pytest.mark.anyio
async def test_openrouter_telemetry_logging():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post.return_value = make_mock_openrouter_response(
        SAMPLE_VALID_RECIPES_JSON, prompt_tokens=200, completion_tokens=500
    )

    config = LLMConfig(
        llm_api_key="test-key",
        llm_model="google/gemma-4-26b-a4b-it:free",
        llm_timeout_seconds=10.0,
    )
    service = OpenRouterLLMService(config=config, client=mock_client)

    with patch("app.llm.openrouter_client.log_llm_telemetry") as mock_telemetry:
        items = [PantryItemInput(name="تخم‌مرغ", quantity=2.0, unit="piece")]
        await service.generate_recipes(items, "dinner", 2, user_id=42, request_id="req-123")

        assert mock_telemetry.called
        call_kwargs = mock_telemetry.call_args.kwargs
        assert call_kwargs["user_id"] == 42
        assert call_kwargs["request_id"] == "req-123"
        assert call_kwargs["model_name"] == "google/gemma-4-26b-a4b-it:free"
        assert call_kwargs["input_tokens"] == 200
        assert call_kwargs["output_tokens"] == 500
        assert call_kwargs["status"] == "success"
