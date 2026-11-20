import asyncio
from datetime import date
from app.llm.factory import get_llm_service
from app.llm.fake import FakeLLMService
from app.llm.interface import (
    LLMInvalidResponse,
    LLMTimeout,
    Nutrition,
    PantryItemInput,
    Recipe,
    RecipeIngredient,
)


def test_fake_llm_service_returns_three_recipes():
    service = FakeLLMService()
    pantry = [
        PantryItemInput(name="تخم‌مرغ", quantity=4.0, unit="piece", expiry_date=date(2026, 11, 20)),
        PantryItemInput(name="گوجه‌فرنگی", quantity=5.0, unit="piece"),
        PantryItemInput(name="برنج", quantity=1.0, unit="kg"),
    ]

    recipes = asyncio.run(
        service.generate_recipes(pantry_items=pantry, meal_type="lunch", servings=2)
    )

    assert isinstance(recipes, list)
    assert len(recipes) == 3

    for recipe in recipes:
        assert isinstance(recipe, Recipe)
        assert recipe.title
        assert recipe.summary
        assert recipe.emoji
        assert recipe.time_minutes > 0
        assert recipe.difficulty in ("easy", "medium", "hard")
        assert recipe.servings == 2
        assert len(recipe.ingredients) > 0
        assert len(recipe.steps) > 0
        assert isinstance(recipe.nutrition, Nutrition)
        assert recipe.nutrition.calories > 0
        assert isinstance(recipe.uses, list)
        assert isinstance(recipe.missing, list)

        # Check ingredients validation
        for ing in recipe.ingredients:
            assert isinstance(ing, RecipeIngredient)
            assert ing.name
            assert ing.amount > 0
            assert ing.unit
            assert isinstance(ing.in_pantry, bool)


def test_factory_returns_fake_by_default(monkeypatch):
    monkeypatch.delenv("LLM_MODE", raising=False)
    service = get_llm_service()
    assert isinstance(service, FakeLLMService)


def test_factory_returns_fake_explicit(monkeypatch):
    monkeypatch.setenv("LLM_MODE", "fake")
    service = get_llm_service()
    assert isinstance(service, FakeLLMService)


def test_factory_returns_real_when_configured(monkeypatch):
    monkeypatch.setenv("LLM_MODE", "real")
    monkeypatch.setenv("LLM_API_KEY", "sk-ant-test-key-12345")
    from app.llm.client import AnthropicLLMService

    service = get_llm_service()
    assert isinstance(service, AnthropicLLMService)


def test_interface_exceptions():
    assert issubclass(LLMTimeout, Exception)
    assert issubclass(LLMInvalidResponse, Exception)
