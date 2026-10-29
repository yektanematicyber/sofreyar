from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.ingredient import IngredientOut


class PantryItemCreate(BaseModel):
    ingredient_id: int
    quantity: float = Field(gt=0)
    unit: str
    expiry_date: date | None = None


class PantryItemUpdate(BaseModel):
    quantity: float | None = Field(default=None, gt=0)
    unit: str | None = None
    expiry_date: date | None = None


class PantryItemOut(BaseModel):
    id: int
    ingredient_id: int
    quantity: float
    unit: str
    expiry_date: date | None
    created_at: datetime
    ingredient: IngredientOut

    model_config = ConfigDict(from_attributes=True)