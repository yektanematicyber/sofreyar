from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Ingredient
from app.schemas.ingredient import IngredientOut

router = APIRouter(prefix="/ingredients", tags=["Ingredients"])


@router.get("/search", response_model=list[IngredientOut])
def search_ingredients(
    q: str = Query(min_length=1),
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    return (
        db.query(Ingredient)
        .filter(Ingredient.name.ilike(f"%{q}%"))
        .order_by(Ingredient.name)
        .limit(limit)
        .all()
    )