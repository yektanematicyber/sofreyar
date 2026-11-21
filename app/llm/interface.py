from datetime import date
from typing import Literal, Protocol
from pydantic import BaseModel, Field

MealType = Literal["breakfast", "lunch", "dinner", "snack"]

class PantryItemInput(BaseModel):
    name: str
    quantity: float
    unit: str                     # g, kg, ml, l, piece
    expiry_date: date | None = None

class RecipeIngredient(BaseModel):
    name: str
    amount: float
    unit: str
    in_pantry: bool

class Nutrition(BaseModel):       # per serving, approximate
    calories: int
    protein_g: float
    fiber_g: float
    carbs_g: float
    fat_g: float

class Recipe(BaseModel):
    title: str
    summary: str
    emoji: str
    time_minutes: int = Field(gt=0)
    difficulty: Literal["easy", "medium", "hard"]
    servings: int = Field(gt=0)
    ingredients: list[RecipeIngredient]
    uses: list[str]               # pantry items the recipe uses
    missing: list[str]            # required items not in the pantry
    steps: list[str]
    nutrition: Nutrition

class LLMTimeout(Exception): ...
class LLMInvalidResponse(Exception): ...
class LLMProviderError(Exception): ...
class LLMAuthenticationError(LLMProviderError): ...
class LLMRateLimitError(LLMProviderError): ...

class LLMService(Protocol):
    async def generate_recipes(
        self, pantry_items: list[PantryItemInput],
        meal_type: MealType, servings: int,
    ) -> list[Recipe]: ...      # exactly 3 recipes
