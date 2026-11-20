import asyncio
import logging
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock

import anthropic
import pytest

from app.llm.client import AnthropicLLMService, _clean_json_text, _parse_and_validate_recipes
from app.llm.config import LLMConfig
from app.llm.interface import (
    LLMInvalidResponse,
    LLMTimeout,
    PantryItemInput,
    Recipe,
)
from app.llm.prompts import build_retry_prompt, build_user_prompt

SAMPLE_VALID_RECIPES_JSON = """[
  {
    "title": "املت گوجه‌فرنگی",
    "summary": "غذای ساده و سریع با تخم‌مرغ و گوجه‌فرنگی.",
    "emoji": "🍳",
    "time_minutes": 15,
    "difficulty": "easy",
    "servings": 2,
    "ingredients": [
      {"name": "تخم‌مرغ", "amount": 4.0, "unit": "piece", "in_pantry": true},
      {"name": "گوجه‌فرنگی", "amount": 3.0, "unit": "piece", "in_pantry": true},
      {"name": "نمک", "amount": 2.0, "unit": "g", "in_pantry": false}
    ],
    "uses": ["تخم‌مرغ", "گوجه‌فرنگی"],
    "missing": ["نمک"],
    "steps": ["گوجه‌ها را سرخ کنید.", "تخم‌مرغ‌ها را اضافه کنید."],
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
      {"name": "ماست", "amount": 200.0, "unit": "g", "in_pantry": true},
      {"name": "خیار", "amount": 2.0, "unit": "piece", "in_pantry": true},
      {"name": "نعناع خشک", "amount": 5.0, "unit": "g", "in_pantry": false}
    ],
    "uses": ["ماست", "خیار"],
    "missing": ["نعناع خشک"],
    "steps": ["خیار را رنده کنید.", "با ماست و نعناع مخلوط کنید."],
    "nutrition": {
      "calories": 120,
      "protein_g": 8.0,
      "fiber_g": 1.0,
      "carbs_g": 12.0,
      "fat_g": 4.0
    }
  }
]"""


def make_mock_message(content_text: str, input_tokens: int = 150, output_tokens: int = 400):
    content_block = MagicMock()
    content_block.text = content_text

    usage_block = MagicMock()
    usage_block.input_tokens = input_tokens
    usage_block.output_tokens = output_tokens

    response = MagicMock()
    response.content = [content_block]
    response.usage = usage_block
    return response


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
    # Only 2 recipes
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

    # Expiry sorting order check: today (پنیر), 1 day (ماست), 10 days (شیر), None (برنج)
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


def test_client_valid_json_success():
    mock_anthropic = MagicMock()
    mock_messages = AsyncMock()
    mock_anthropic.messages = mock_messages
    mock_messages.create.return_value = make_mock_message(SAMPLE_VALID_RECIPES_JSON)

    config = LLMConfig(llm_api_key="test-key", llm_timeout_seconds=5.0)
    service = AnthropicLLMService(client=mock_anthropic, config=config)

    items = [PantryItemInput(name="تخم‌مرغ", quantity=4.0, unit="piece")]
    recipes = asyncio.run(service.generate_recipes(items, "dinner", 2))

    assert len(recipes) == 3
    assert recipes[0].title == "املت گوجه‌فرنگی"
    assert mock_messages.create.await_count == 1


def test_client_malformed_json_retry_succeeds():
    mock_anthropic = MagicMock()
    mock_messages = AsyncMock()
    mock_anthropic.messages = mock_messages

    # 1st call returns malformed JSON, 2nd call returns valid 3-recipe JSON
    mock_messages.create.side_effect = [
        make_mock_message("NOT A JSON OUTPUT! Here are some recipes..."),
        make_mock_message(SAMPLE_VALID_RECIPES_JSON),
    ]

    config = LLMConfig(llm_api_key="test-key", llm_timeout_seconds=5.0)
    service = AnthropicLLMService(client=mock_anthropic, config=config)

    items = [PantryItemInput(name="تخم‌مرغ", quantity=4.0, unit="piece")]
    recipes = asyncio.run(service.generate_recipes(items, "lunch", 2))

    assert len(recipes) == 3
    assert mock_messages.create.await_count == 2

    # Verify retry prompt includes error message
    retry_call_args = mock_messages.create.call_args_list[1]
    messages_payload = retry_call_args.kwargs["messages"]
    retry_text = messages_payload[0]["content"]
    assert "پاسخ قبلی شما در اعتبارسنجی با خطای زیر مواجه شد" in retry_text
    assert "Malformed JSON" in retry_text


def test_client_two_failures_raises_llm_invalid_response():
    mock_anthropic = MagicMock()
    mock_messages = AsyncMock()
    mock_anthropic.messages = mock_messages

    # Both calls return invalid responses
    mock_messages.create.side_effect = [
        make_mock_message("Invalid response 1"),
        make_mock_message("Invalid response 2"),
    ]

    config = LLMConfig(llm_api_key="test-key", llm_timeout_seconds=5.0)
    service = AnthropicLLMService(client=mock_anthropic, config=config)

    items = [PantryItemInput(name="تخم‌مرغ", quantity=4.0, unit="piece")]

    with pytest.raises(LLMInvalidResponse, match="LLM generated invalid response after retry"):
        asyncio.run(service.generate_recipes(items, "dinner", 2))

    assert mock_messages.create.await_count == 2


def test_client_wrong_recipe_count_retry_fails():
    mock_anthropic = MagicMock()
    mock_messages = AsyncMock()
    mock_anthropic.messages = mock_messages

    # Returns 1 recipe on both calls
    one_recipe = """[
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
      }
    ]"""

    mock_messages.create.side_effect = [
        make_mock_message(one_recipe),
        make_mock_message(one_recipe),
    ]

    config = LLMConfig(llm_api_key="test-key", llm_timeout_seconds=5.0)
    service = AnthropicLLMService(client=mock_anthropic, config=config)

    items = [PantryItemInput(name="تخم‌مرغ", quantity=4.0, unit="piece")]

    with pytest.raises(LLMInvalidResponse, match="Expected exactly 3 recipes, but received 1"):
        asyncio.run(service.generate_recipes(items, "dinner", 2))

    assert mock_messages.create.await_count == 2


def test_client_timeout_raises_llm_timeout():
    mock_anthropic = MagicMock()
    mock_messages = AsyncMock()
    mock_anthropic.messages = mock_messages

    # Simulate anthropic timeout
    mock_messages.create.side_effect = anthropic.APITimeoutError(request=MagicMock())

    config = LLMConfig(llm_api_key="test-key", llm_timeout_seconds=5.0)
    service = AnthropicLLMService(client=mock_anthropic, config=config)

    items = [PantryItemInput(name="تخم‌مرغ", quantity=4.0, unit="piece")]

    with pytest.raises(LLMTimeout, match="timed out after 5.0 seconds"):
        asyncio.run(service.generate_recipes(items, "dinner", 2))


def test_client_telemetry_logging(caplog):
    mock_anthropic = MagicMock()
    mock_messages = AsyncMock()
    mock_anthropic.messages = mock_messages
    mock_messages.create.return_value = make_mock_message(
        SAMPLE_VALID_RECIPES_JSON, input_tokens=220, output_tokens=550
    )

    config = LLMConfig(llm_api_key="test-key", llm_timeout_seconds=5.0)
    service = AnthropicLLMService(client=mock_anthropic, config=config)

    with caplog.at_level(logging.INFO, logger="safreyar.llm"):
        items = [PantryItemInput(name="تخم‌مرغ", quantity=4.0, unit="piece")]
        asyncio.run(service.generate_recipes(items, "dinner", 2))

    # Verify telemetry metadata logged without leaking pantry content
    assert any("LLM call completed" in record.message for record in caplog.records)
    assert any("input_tokens=220" in record.message for record in caplog.records)
    assert any("output_tokens=550" in record.message for record in caplog.records)
    # Ensure personal content is NOT logged
    assert not any("تخم‌مرغ" in record.message for record in caplog.records)
