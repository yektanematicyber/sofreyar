from pydantic import BaseModel, ConfigDict


class IngredientBase(BaseModel):
    name: str
    category: str | None = None
    default_unit: str | None = None


class IngredientCreate(IngredientBase):
    pass


class IngredientOut(IngredientBase):
    id: int

    model_config = ConfigDict(from_attributes=True)