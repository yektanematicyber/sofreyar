
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Ingredient, PantryItem, User
from app.schemas.pantry_item import (
    PantryItemCreate,
    PantryItemOut,
    PantryItemUpdate,
)

router = APIRouter(prefix="/pantry", tags=["Pantry"])


@router.post("", response_model=PantryItemOut, status_code=status.HTTP_201_CREATED)
def add_item(
    data: PantryItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ingredient = db.get(Ingredient, data.ingredient_id)
    if ingredient is None:
        raise HTTPException(status_code=404, detail="Ingredient not found")

    item = PantryItem(
        user_id=current_user.id,
        **data.model_dump(),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("", response_model=list[PantryItemOut])
def list_items(
    sort: Literal["id", "expiry"] = Query(
        default="id",
        description="id: به ترتیب افزودن | expiry: نزدیک‌ترین تاریخ انقضا اول",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(PantryItem).filter(PantryItem.user_id == current_user.id)

    if sort == "expiry":
        query = query.order_by(
            PantryItem.expiry_date.asc().nulls_last(),
            PantryItem.id,
        )
    else:
        query = query.order_by(PantryItem.id)

    return query.all()


def get_user_item(
    item_id: int,
    db: Session,
    user_id: int,
) -> PantryItem:
    item = (
        db.query(PantryItem)
        .filter(
            PantryItem.id == item_id,
            PantryItem.user_id == user_id,
        )
        .first()
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Pantry item not found")
    return item


@router.patch("/{item_id}", response_model=PantryItemOut)
def update_item(
    item_id: int,
    data: PantryItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = get_user_item(item_id, db, current_user.id)

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(item, field, value)

    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = get_user_item(item_id, db, current_user.id)
    db.delete(item)
    db.commit()
