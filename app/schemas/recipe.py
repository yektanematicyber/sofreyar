from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

MealType = Literal["breakfast", "lunch", "dinner", "snack"]


class SuggestionRequest(BaseModel):
    meal_type: MealType = Field(
        ...,
        description="نوع وعده غذایی: breakfast, lunch, dinner, snack",
        examples=["lunch"],
    )
    servings: int = Field(
        default=2,
        gt=0,
        description="تعداد نفرات (باید بزرگتر از صفر باشد)",
        examples=[2],
    )


class RecipeIngredientOut(BaseModel):
    name: str
    amount: float
    unit: str
    in_pantry: bool

    model_config = ConfigDict(from_attributes=True)


class NutritionOut(BaseModel):
    calories: int
    protein_g: float
    fiber_g: float
    carbs_g: float
    fat_g: float

    model_config = ConfigDict(from_attributes=True)


class RecipeOut(BaseModel):
    id: int
    user_id: int
    title: str
    summary: str
    emoji: str
    cooking_time: int = Field(description="زمان پخت به دقیقه")
    time_minutes: int | None = Field(default=None, description="نام جایگزین برای زمان پخت")
    difficulty: str
    servings: int
    ingredients: list[RecipeIngredientOut]
    uses: list[str]
    missing: list[str]
    steps: list[str]
    nutrition: NutritionOut
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    def model_post_init(self, __context):
        if self.time_minutes is None:
            self.time_minutes = self.cooking_time


class ErrorResponse(BaseModel):
    detail: str
    error_code: str
