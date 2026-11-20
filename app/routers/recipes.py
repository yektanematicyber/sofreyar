import logging

from fastapi import APIRouter, Depends, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.exceptions import DatabaseException, RecipeNotFoundException
from app.models import Recipe, User
from app.schemas.recipe import RecipeOut

logger = logging.getLogger("safreyar.recipes")

router = APIRouter(prefix="/recipes", tags=["Recipes"])


@router.get(
    "/{recipe_id}",
    response_model=RecipeOut,
    status_code=status.HTTP_200_OK,
    summary="Get saved recipe details by ID",
)
def get_recipe_by_id(
    recipe_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RecipeOut:
    """Retrieves full details of a saved recipe.

    Security:
      - Authenticated user only
      - Strict ownership check: Returns 404 RECIPE_NOT_FOUND if the recipe
        does not exist or belongs to another user.
      - Zero LLM calls on retrieval.
    """
    try:
        recipe = db.get(Recipe, recipe_id)
    except SQLAlchemyError as err:
        logger.exception("Database error while fetching recipe_id=%d: %s", recipe_id, err)
        raise DatabaseException() from err

    if recipe is None or recipe.user_id != current_user.id:
        raise RecipeNotFoundException()

    return recipe
