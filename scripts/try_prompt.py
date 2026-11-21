#!/usr/bin/env python3
"""Diagnostic script for manual prompt review against OpenRouter API.

Runs 16 diverse, representative sample pantries (sparse, large, near-expiry, vegetarian,
English aliases, single large quantities, breakfast/lunch/dinner/snack, single/multi servings)
and prints formatted outputs with latency and token telemetry for manual quality evaluation.

Usage:
    python scripts/try_prompt.py
    python scripts/try_prompt.py --limit 3
    python scripts/try_prompt.py --fake   # Test run with FakeLLMService
"""

import argparse
import asyncio
import os
import sys
import time
from datetime import date, timedelta
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.llm.openrouter_client import OpenRouterLLMService
from app.llm.config import get_llm_config
from app.llm.fake import FakeLLMService
from app.llm.interface import LLMService, MealType, PantryItemInput, Recipe

TODAY = date.today()

SAMPLE_SCENARIOS: list[dict] = [
    {
        "id": 1,
        "name": "خیلی کم و حداقلی (فقط تخم‌مرغ)",
        "meal_type": "breakfast",
        "servings": 2,
        "items": [
            PantryItemInput(name="تخم‌مرغ", quantity=4.0, unit="piece"),
        ],
    },
    {
        "id": 2,
        "name": "حداقلی خنک (ماست و خیار رو به انقضا)",
        "meal_type": "snack",
        "servings": 2,
        "items": [
            PantryItemInput(name="ماست کم‌چرب", quantity=400.0, unit="g", expiry_date=TODAY + timedelta(days=1)),
            PantryItemInput(name="خیار بوته‌ای", quantity=3.0, unit="piece", expiry_date=TODAY + timedelta(days=2)),
        ],
    },
    {
        "id": 3,
        "name": "انبار اصیل ایرانی (زرشک‌پلو و مرغ)",
        "meal_type": "lunch",
        "servings": 3,
        "items": [
            PantryItemInput(name="سینه مرغ", quantity=500.0, unit="g", expiry_date=TODAY + timedelta(days=3)),
            PantryItemInput(name="برنج طارم", quantity=2.0, unit="kg"),
            PantryItemInput(name="پیاز سفید", quantity=4.0, unit="piece"),
            PantryItemInput(name="رب گوجه‌فرنگی", quantity=300.0, unit="g"),
            PantryItemInput(name="زرشک", quantity=100.0, unit="g"),
        ],
    },
    {
        "id": 4,
        "name": "اضطراری رو به انقضا (شیر و اسفناج امروز)",
        "meal_type": "dinner",
        "servings": 2,
        "items": [
            PantryItemInput(name="شیر کم‌چرب", quantity=1.0, unit="l", expiry_date=TODAY),
            PantryItemInput(name="اسفناج تازه", quantity=400.0, unit="g", expiry_date=TODAY + timedelta(days=1)),
            PantryItemInput(name="تخم‌مرغ", quantity=3.0, unit="piece", expiry_date=TODAY + timedelta(days=5)),
            PantryItemInput(name="سیر", quantity=2.0, unit="piece"),
        ],
    },
    {
        "id": 5,
        "name": "گیاه‌خواری سنتی (عدس‌پلو و حبوبات)",
        "meal_type": "lunch",
        "servings": 4,
        "items": [
            PantryItemInput(name="عدس سبز", quantity=500.0, unit="g"),
            PantryItemInput(name="برنج", quantity=1.5, unit="kg"),
            PantryItemInput(name="کشمش پلویی", quantity=200.0, unit="g"),
            PantryItemInput(name="پیاز", quantity=3.0, unit="piece"),
            PantryItemInput(name="دارچین و زردچوبه", quantity=50.0, unit="g"),
        ],
    },
    {
        "id": 6,
        "name": "صبحانه مقوی و سنتی",
        "meal_type": "breakfast",
        "servings": 2,
        "items": [
            PantryItemInput(name="پنیر لیقوان", quantity=200.0, unit="g", expiry_date=TODAY + timedelta(days=7)),
            PantryItemInput(name="گردو", quantity=100.0, unit="g"),
            PantryItemInput(name="گوجه‌فرنگی", quantity=2.0, unit="piece", expiry_date=TODAY + timedelta(days=2)),
            PantryItemInput(name="خیار", quantity=2.0, unit="piece"),
            PantryItemInput(name="نان سنگک", quantity=1.0, unit="piece"),
        ],
    },
    {
        "id": 7,
        "name": "عصرانه شیرین و رژیمی",
        "meal_type": "snack",
        "servings": 2,
        "items": [
            PantryItemInput(name="سیب قرمز", quantity=3.0, unit="piece", expiry_date=TODAY + timedelta(days=4)),
            PantryItemInput(name="جو دو سر پرک", quantity=300.0, unit="g"),
            PantryItemInput(name="عسل طبیعی", quantity=150.0, unit="g"),
            PantryItemInput(name="دارچین", quantity=30.0, unit="g"),
        ],
    },
    {
        "id": 8,
        "name": "اقلام کنسروی و نامتعارف",
        "meal_type": "dinner",
        "servings": 2,
        "items": [
            PantryItemInput(name="کنسرو تن ماهی", quantity=1.0, unit="piece"),
            PantryItemInput(name="کنسرو ذرت شیرین", quantity=1.0, unit="piece"),
            PantryItemInput(name="سس مایونز", quantity=200.0, unit="g", expiry_date=TODAY + timedelta(days=10)),
            PantryItemInput(name="سیب‌زمینی", quantity=3.0, unit="piece"),
        ],
    },
    {
        "id": 9,
        "name": "ورزشی و پرپروتئین (تک‌نفره)",
        "meal_type": "dinner",
        "servings": 1,
        "items": [
            PantryItemInput(name="فیله مرغ", quantity=300.0, unit="g", expiry_date=TODAY + timedelta(days=2)),
            PantryItemInput(name="کلم بروکلی", quantity=200.0, unit="g", expiry_date=TODAY + timedelta(days=1)),
            PantryItemInput(name="سفیده تخم‌مرغ", quantity=4.0, unit="piece"),
            PantryItemInput(name="روغن زیتون", quantity=50.0, unit="ml"),
        ],
    },
    {
        "id": 10,
        "name": "دریایی و معطر",
        "meal_type": "lunch",
        "servings": 2,
        "items": [
            PantryItemInput(name="ماهی قزل‌آلا", quantity=2.0, unit="piece", expiry_date=TODAY + timedelta(days=1)),
            PantryItemInput(name="شوید تازه", quantity=150.0, unit="g", expiry_date=TODAY),
            PantryItemInput(name="برنج", quantity=500.0, unit="g"),
            PantryItemInput(name="سیر و لیمو ترش", quantity=3.0, unit="piece"),
        ],
    },
    {
        "id": 11,
        "name": "عصرانه زمستانی و آش",
        "meal_type": "dinner",
        "servings": 4,
        "items": [
            PantryItemInput(name="سبزی آش", quantity=500.0, unit="g", expiry_date=TODAY + timedelta(days=2)),
            PantryItemInput(name="نخود و لوبیا پخته", quantity=300.0, unit="g"),
            PantryItemInput(name="رشته آشی", quantity=200.0, unit="g"),
            PantryItemInput(name="کشک", quantity=200.0, unit="g", expiry_date=TODAY + timedelta(days=5)),
        ],
    },
    {
        "id": 12,
        "name": "انبار متنوع و مفصل خانوادگی (۶ نفره)",
        "meal_type": "dinner",
        "servings": 6,
        "items": [
            PantryItemInput(name="گوشت چرخ‌کرده", quantity=600.0, unit="g", expiry_date=TODAY + timedelta(days=2)),
            PantryItemInput(name="بادمجان", quantity=5.0, unit="piece", expiry_date=TODAY + timedelta(days=3)),
            PantryItemInput(name="گوجه‌فرنگی", quantity=6.0, unit="piece", expiry_date=TODAY + timedelta(days=4)),
            PantryItemInput(name="سیب‌زمینی", quantity=5.0, unit="piece"),
            PantryItemInput(name="پیاز", quantity=4.0, unit="piece"),
            PantryItemInput(name="ماکارونی", quantity=700.0, unit="g"),
        ],
    },
    {
        "id": 13,
        "name": "حجم زیاد از یک ماده غذایی (انبوه بادمجان)",
        "meal_type": "dinner",
        "servings": 3,
        "items": [
            PantryItemInput(name="بادمجان قلمی", quantity=4.0, unit="kg", expiry_date=TODAY + timedelta(days=3)),
            PantryItemInput(name="سیر", quantity=1.0, unit="piece"),
            PantryItemInput(name="گوجه‌فرنگی", quantity=3.0, unit="piece"),
            PantryItemInput(name="تخم‌مرغ", quantity=2.0, unit="piece"),
        ],
    },
    {
        "id": 14,
        "name": "نام‌های انگلیسی / فینگیلیش و بدون تاریخ انقضا",
        "meal_type": "lunch",
        "servings": 2,
        "items": [
            PantryItemInput(name="Chicken Breast", quantity=400.0, unit="g"),
            PantryItemInput(name="Olive Oil", quantity=100.0, unit="ml"),
            PantryItemInput(name="Garlic", quantity=2.0, unit="piece"),
            PantryItemInput(name="Rice", quantity=500.0, unit="g"),
        ],
    },
    {
        "id": 15,
        "name": "چندین قلم اضطراری همزمان در آستانه انقضا (امروز و فردا)",
        "meal_type": "dinner",
        "servings": 2,
        "items": [
            PantryItemInput(name="گوشت چرخ‌کرده", quantity=250.0, unit="g", expiry_date=TODAY),
            PantryItemInput(name="قارچ تازه", quantity=200.0, unit="g", expiry_date=TODAY),
            PantryItemInput(name="خامه صبحانه", quantity=150.0, unit="g", expiry_date=TODAY + timedelta(days=1)),
            PantryItemInput(name="فلفل دلمه‌ای", quantity=1.0, unit="piece", expiry_date=TODAY + timedelta(days=1)),
            PantryItemInput(name="پاستا پنه", quantity=300.0, unit="g"),
        ],
    },
    {
        "id": 16,
        "name": "واحدهای متنوع (لیتر، کیلوگرم، قاشق، عدد)",
        "meal_type": "breakfast",
        "servings": 2,
        "items": [
            PantryItemInput(name="آرد گندم", quantity=0.5, unit="kg"),
            PantryItemInput(name="شیر پاستوریزه", quantity=0.25, unit="l"),
            PantryItemInput(name="تخم‌مرغ", quantity=2.0, unit="piece"),
            PantryItemInput(name="شکر", quantity=40.0, unit="g"),
            PantryItemInput(name="روغن", quantity=30.0, unit="ml"),
        ],
    },
]


def print_recipe(recipe: Recipe, index: int):
    print(f"\n   [{index}] {recipe.emoji} {recipe.title}")
    print(f"       ⏱️ زمان: {recipe.time_minutes} دقیقه | 📊 سختی: {recipe.difficulty} | 👥 وعده: {recipe.servings} نفر")
    print(f"       📝 خلاصه: {recipe.summary}")
    print(f"       🥗 اقلام انبار (Uses): {', '.join(recipe.uses) if recipe.uses else 'هیچ'}")
    print(f"       🛒 کسری‌ها (Missing): {', '.join(recipe.missing) if recipe.missing else 'هیچ'}")
    print("       🥣 مواد لازم:")
    for ing in recipe.ingredients:
        status_symbol = "✅" if ing.in_pantry else "❌"
        print(f"          {status_symbol} {ing.name}: {ing.amount} {ing.unit}")
    print(f"       🔥 ارزش غذایی (هر وعده): {recipe.nutrition.calories} کالری | پروتئین: {recipe.nutrition.protein_g}g | کربوهیدرات: {recipe.nutrition.carbs_g}g | چربی: {recipe.nutrition.fat_g}g | فیبر: {recipe.nutrition.fiber_g}g")
    print("       🍳 مراحل پخت:")
    for s_idx, step in enumerate(recipe.steps, 1):
        print(f"          {s_idx}. {step}")


async def run_diagnostics(limit: int | None = None, use_fake: bool = False):
    config = get_llm_config()

    if use_fake:
        print("\n🧪 Using FakeLLMService (offline deterministic mode)")
        service: LLMService = FakeLLMService()
    else:
        if not config.llm_api_key or config.llm_api_key.startswith("your-"):
            print("\n❌ Error: LLM_API_KEY is not configured in .env!")
            print("To test against real OpenRouter API, set LLM_API_KEY in .env.")
            print("Alternatively, pass --fake to run against FakeLLMService.")
            sys.exit(1)
        print(f"\n🚀 Using real OpenRouter API (model: {config.llm_model})")
        service = OpenRouterLLMService(config=config)

    scenarios = SAMPLE_SCENARIOS[:limit] if limit else SAMPLE_SCENARIOS
    print(f"Testing {len(scenarios)} sample pantry scenarios...\n" + "=" * 60)

    total_start = time.time()
    successful = 0

    for sc in scenarios:
        print(f"\n🏷️ سناریو #{sc['id']}: {sc['name']}")
        print(f"   وعده: {sc['meal_type']} | تعداد نفرات: {sc['servings']}")
        print(f"   موجودی ورودی: {', '.join(f'{item.name} ({item.quantity} {item.unit})' for item in sc['items'])}")

        start_call = time.time()
        try:
            recipes = await service.generate_recipes(
                pantry_items=sc["items"],
                meal_type=sc["meal_type"],
                servings=sc["servings"],
            )
            duration = round(time.time() - start_call, 2)
            print(f"   ⚡ زمان پاسخ: {duration} ثانیه | تعداد دستورها: {len(recipes)}")

            for idx, r in enumerate(recipes, start=1):
                print_recipe(r, idx)

            successful += 1
        except Exception as err:
            duration = round(time.time() - start_call, 2)
            print(f"   ❌ خطا پس از {duration} ثانیه: {type(err).__name__} - {err}")

        print("-" * 60)

    total_time = round(time.time() - total_start, 2)
    print(f"\n📊 نتیجه کل: {successful}/{len(scenarios)} سناریو با موفقیت انجام شد (زمان کل: {total_time} ثانیه).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Try Safreyar LLM meal suggestion prompts")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of scenarios to run")
    parser.add_argument("--fake", action="store_true", help="Run against FakeLLMService instead of real API")
    args = parser.parse_args()

    asyncio.run(run_diagnostics(limit=args.limit, use_fake=args.fake))
