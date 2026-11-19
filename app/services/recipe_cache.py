import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.llm.interface import Recipe as LLMRecipe
from app.models.pantry_item import PantryItem, utc_now_naive
from app.models.recipe import Recipe

# Configurable cache expiration in hours (default: 24.0 hours)
DEFAULT_CACHE_EXPIRE_HOURS = 24.0


def get_cache_expire_hours() -> float:
    try:
        return float(os.getenv("RECIPE_CACHE_EXPIRE_HOURS", str(DEFAULT_CACHE_EXPIRE_HOURS)))
    except (ValueError, TypeError):
        return DEFAULT_CACHE_EXPIRE_HOURS


def compute_recipe_cache_hash(
    user_id: int,
    meal_type: str,
    servings: int,
    pantry_items: Sequence[PantryItem],
    model_version: str = "claude-3-5-sonnet:v1",
) -> str:
    """Computes a deterministic, collision-resistant SHA-256 cache key.

    Incorporates user_id, meal_type, servings, model version, and normalized/sorted
    pantry inventory (including IDs, quantities, units, and expiry dates).
    Any modification in quantity, unit, or expiration produces a distinct hash.
    """
    normalized_items = []
    for item in pantry_items:
        ing_id = item.ingredient_id
        name = item.ingredient.name.strip().lower() if item.ingredient else ""
        quantity = round(float(item.quantity), 4)
        unit = item.unit.strip().lower()
        expiry = item.expiry_date.isoformat() if item.expiry_date else "none"
        normalized_items.append((ing_id, name, quantity, unit, expiry))

    # Sort deterministically by ingredient_id, then name, then unit
    normalized_items.sort(key=lambda x: (x[0], x[1], x[3]))

    cache_dict = {
        "user_id": user_id,
        "meal_type": meal_type.strip().lower(),
        "servings": int(servings),
        "model_version": model_version.strip(),
        "pantry": [
            {
                "id": ing_id,
                "name": name,
                "qty": qty,
                "unit": unit,
                "expiry": expiry,
            }
            for (ing_id, name, qty, unit, expiry) in normalized_items
        ],
    }

    canonical_json = json.dumps(cache_dict, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def get_cached_recipes(
    db: Session,
    user_id: int,
    cache_hash: str,
) -> list[Recipe] | None:
    """Retrieves cached recipes from PostgreSQL if matching and not expired."""
    expire_hours = get_cache_expire_hours()
    cutoff_time = utc_now_naive() - timedelta(hours=expire_hours)

    stmt = (
        select(Recipe)
        .where(
            Recipe.user_id == user_id,
            Recipe.cache_hash == cache_hash,
            Recipe.created_at >= cutoff_time,
        )
        .order_by(Recipe.id.asc())
    )
    cached = list(db.scalars(stmt).all())
    if len(cached) == 3:
        return cached

    return None


def save_recipes_to_db(
    db: Session,
    user_id: int,
    recipes: list[LLMRecipe],
    cache_hash: str,
) -> list[Recipe]:
    """Persists validated LLM recipes to PostgreSQL associated with the user and cache hash."""
    db_records: list[Recipe] = []
    for r in recipes:
        db_recipe = Recipe(
            user_id=user_id,
            title=r.title,
            summary=r.summary,
            emoji=r.emoji,
            cooking_time=r.time_minutes,
            difficulty=r.difficulty,
            servings=r.servings,
            ingredients=[ing.model_dump() for ing in r.ingredients],
            uses=r.uses,
            missing=r.missing,
            steps=r.steps,
            nutrition=r.nutrition.model_dump(),
            cache_hash=cache_hash,
        )
        db.add(db_recipe)
        db_records.append(db_recipe)

    db.commit()
    for rec in db_records:
        db.refresh(rec)

    return db_records
