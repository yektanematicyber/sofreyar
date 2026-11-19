from typing import Any

from app.llm.interface import (
    LLMService,
    MealType,
    Nutrition,
    PantryItemInput,
    Recipe,
    RecipeIngredient,
)
from app.llm.telemetry import log_llm_telemetry


class FakeLLMService(LLMService):
    """Deterministic fake LLM service returning 3 fixed, realistic Persian recipes.

    Designed for offline development, API testing, and parallel frontend development.
    Empty pantry checks are handled at the API layer.
    """

    async def generate_recipes(
        self,
        pantry_items: list[PantryItemInput],
        meal_type: MealType,
        servings: int,
        user_id: int | None = None,
        request_id: str | None = None,
        **kwargs: Any,
    ) -> list[Recipe]:
        pantry_names = {item.name.strip().lower() for item in pantry_items}
        effective_servings = max(1, servings)

        def check_ingredient(name: str, base_amount: float, unit: str) -> tuple[RecipeIngredient, bool]:
            # Simple substring/inclusion check against user's pantry
            is_present = any(name.lower() in p or p in name.lower() for p in pantry_names)
            ingredient = RecipeIngredient(
                name=name,
                amount=round(base_amount * effective_servings, 2),
                unit=unit,
                in_pantry=is_present,
            )
            return ingredient, is_present

        # Recipe 1: Tomato Omelette (املت گوجه‌فرنگی)
        r1_specs = [
            ("تخم‌مرغ", 2.0, "piece"),
            ("گوجه‌فرنگی", 2.0, "piece"),
            ("روغن مایع", 10.0, "ml"),
            ("نمک و فلفل سیاه", 1.0, "g"),
        ]
        r1_ingredients: list[RecipeIngredient] = []
        r1_uses: list[str] = []
        r1_missing: list[str] = []
        for name, amount, unit in r1_specs:
            ing, present = check_ingredient(name, amount, unit)
            r1_ingredients.append(ing)
            if present:
                # Add matched pantry name or ingredient name
                matched = next((p.name for p in pantry_items if name.lower() in p.name.lower() or p.name.lower() in name.lower()), name)
                if matched not in r1_uses:
                    r1_uses.append(matched)
            else:
                r1_missing.append(name)

        recipe1 = Recipe(
            title="املت گوجه‌فرنگی قهوه‌خانه‌ای",
            summary="یک املت اصیل و لذیذ ایرانی با گوجه‌فرنگی پخته و تخم‌مرغ تازه، مناسب برای صبحانه یا شام سریع.",
            emoji="🍳",
            time_minutes=15,
            difficulty="easy",
            servings=effective_servings,
            ingredients=r1_ingredients,
            uses=r1_uses,
            missing=r1_missing,
            steps=[
                "گوجه‌فرنگی‌ها را رنده یا نگینی خرد کرده و در تابه تفت دهید تا آب آن به آرامی تبخیر شود.",
                "روغن مایع، نمک و فلفل را به گوجه‌ها اضافه کرده و کمی تفت دهید تا روغن خوش‌رنگ شود.",
                "تخم‌مرغ‌ها را روی گوجه‌ها شکسته، به آرامی مخلوط کنید و بگذارید با حرارت ملایم ببندد.",
            ],
            nutrition=Nutrition(
                calories=210,
                protein_g=13.0,
                fiber_g=2.0,
                carbs_g=6.0,
                fat_g=15.0,
            ),
        )

        # Recipe 2: Chicken Rice (چلو مرغ زعفرانی ساده)
        r2_specs = [
            ("سینه مرغ", 150.0, "g"),
            ("برنج", 100.0, "g"),
            ("پیاز", 0.5, "piece"),
            ("زعفران و زردچوبه", 1.0, "g"),
            ("روغن یا کره", 15.0, "g"),
        ]
        r2_ingredients = []
        r2_uses = []
        r2_missing = []
        for name, amount, unit in r2_specs:
            ing, present = check_ingredient(name, amount, unit)
            r2_ingredients.append(ing)
            if present:
                matched = next((p.name for p in pantry_items if name.lower() in p.name.lower() or p.name.lower() in name.lower()), name)
                if matched not in r2_uses:
                    r2_uses.append(matched)
            else:
                r2_missing.append(name)

        recipe2 = Recipe(
            title="زرشک پلو با مرغ ساده",
            summary="خوراک مرغ زعفرانی خوش‌عطر همراه با پلو ایرانی، یک وعده مقوی و سیرکننده برای ناهار یا شام.",
            emoji="🍗",
            time_minutes=45,
            difficulty="medium",
            servings=effective_servings,
            ingredients=r2_ingredients,
            uses=r2_uses,
            missing=r2_missing,
            steps=[
                "پیاز را نگینی خرد کرده و تفت دهید، سپس تکه‌های مرغ را با زردچوبه و نمک به آن اضافه کنید.",
                "کمی آب جوش و زعفران دم‌کرده اضافه کرده و درب قابلمه را بگذارید تا مرغ با حرارت ملایم مغزپخت شود.",
                "برنج را به صورت کته یا آبکش دم کنید و همراه مرغ زعفرانی سرو نمایید.",
            ],
            nutrition=Nutrition(
                calories=490,
                protein_g=35.0,
                fiber_g=2.5,
                carbs_g=55.0,
                fat_g=13.0,
            ),
        )

        # Recipe 3: Yogurt and Cold Chicken / Chilled Cucumber Soup (سالاد ماست و مرغ خنک)
        r3_specs = [
            ("ماست کم‌چرب", 150.0, "g"),
            ("سینه مرغ پخته", 100.0, "g"),
            ("خیار", 1.0, "piece"),
            ("نعنا خشک و نمک", 2.0, "g"),
            ("گردو خرد شده", 15.0, "g"),
        ]
        r3_ingredients = []
        r3_uses = []
        r3_missing = []
        for name, amount, unit in r3_specs:
            ing, present = check_ingredient(name, amount, unit)
            r3_ingredients.append(ing)
            if present:
                matched = next((p.name for p in pantry_items if name.lower() in p.name.lower() or p.name.lower() in name.lower()), name)
                if matched not in r3_uses:
                    r3_uses.append(matched)
            else:
                r3_missing.append(name)

        recipe3 = Recipe(
            title="ماست و مرغ خنک با سبزی معطر",
            summary="ترکیب خنک، رژیمی و پروتئینی از تکه‌های مرغ سرد، ماست، خیار تازه و نعنا خشک، مناسب برای شام سبک یا عصرانه.",
            emoji="🥗",
            time_minutes=10,
            difficulty="easy",
            servings=effective_servings,
            ingredients=r3_ingredients,
            uses=r3_uses,
            missing=r3_missing,
            steps=[
                "سینه مرغ پخته و سرد شده را ریش‌ریش کرده یا به اندازه لقمه‌ای خرد کنید.",
                "خیار را نگینی ریز خرد کنید و همراه مرغ به ماست اضافه کنید.",
                "نعنا خشک، نمک و در صورت تمایل گردو خرد شده را اضافه کرده و هم بزنید تا کاملاً مزه‌دار شود.",
            ],
            nutrition=Nutrition(
                calories=230,
                protein_g=24.0,
                fiber_g=1.5,
                carbs_g=10.0,
                fat_g=7.0,
            ),
        )

        recipes = [recipe1, recipe2, recipe3]
        log_llm_telemetry(
            user_id=user_id,
            request_id=request_id,
            model_name="fake-llm",
            input_tokens=100,
            output_tokens=300,
            latency_ms=10.0,
            status="success",
            retry_required=False,
            from_cache=False,
            is_fake=True,
        )
        return recipes
