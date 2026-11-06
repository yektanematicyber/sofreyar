# AI Recipe & Meal Planning Schemas Reference

## 1. Pydantic V2 Schemas for AI Meal Generation

```python
from pydantic import BaseModel, Field

class NutritionSummary(BaseModel):
    calories: int = Field(ge=0)
    protein_grams: float = Field(ge=0)
    carbs_grams: float = Field(ge=0)
    fat_grams: float = Field(ge=0)

class RecipeIngredientItem(BaseModel):
    ingredient_name: str
    quantity: float
    unit: str
    is_in_pantry: bool = True
    suggested_substitution: str | None = None

class GeneratedRecipe(BaseModel):
    title: str = Field(description="Name of the dish (e.g. املت گوجه فرنگی)")
    description: str
    prep_time_minutes: int
    cook_time_minutes: int
    servings: int = 2
    ingredients: list[RecipeIngredientItem]
    instructions: list[str]
    nutrition: NutritionSummary
    urgency_reason: str | None = Field(
        default=None,
        description="Reason why this was suggested (e.g. 'Uses 2 items expiring tomorrow')"
    )

class MealSuggestionResponse(BaseModel):
    suggestions: list[GeneratedRecipe]
    total_pantry_utilization_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Ratio of pantry items utilized across suggestions"
    )
```

---

## 2. LLM System Prompt Template

```markdown
You are Safreyar's Culinary Intelligence Agent. Your goal is to generate delicious, healthy, Persian and international recipes maximizing the user's available pantry ingredients while minimizing food waste.

### Guidelines:
1. Prioritize items marked with imminent expiry dates.
2. If essential ingredients are missing, suggest natural Persian kitchen substitutions or list them clearly as missing items for the shopping list.
3. Keep instructions step-by-step, actionable, and culturally accurate.
4. Output strictly valid JSON matching the `MealSuggestionResponse` schema.
```
