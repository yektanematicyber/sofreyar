import logging
import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.dependencies import get_current_user
from app.exceptions import (
    EmptyPantryException,
    InvalidLLMResponseException,
    LLMProviderException,
    LLMTimeoutException,
)
from app.llm import LLMInvalidResponse, LLMTimeout, PantryItemInput, get_llm_service
from app.llm.telemetry import log_llm_telemetry
from app.models import PantryItem, User
from app.rate_limiter import suggestions_rate_limiter
from app.schemas.recipe import RecipeOut, SuggestionRequest
from app.services.recipe_cache import (
    compute_recipe_cache_hash,
    get_cached_recipes,
    save_recipes_to_db,
)

logger = logging.getLogger("safreyar.suggestions")

router = APIRouter(prefix="/suggestions", tags=["Meal Suggestions"])


@router.post(
    "",
    response_model=list[RecipeOut],
    status_code=status.HTTP_200_OK,
    summary="Suggest 3 recipes based on current pantry items",
)
async def generate_suggestions(
    payload: SuggestionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[RecipeOut]:
    """Generates 3 personalized Persian recipes based on user pantry items.

    Features:
      - Authenticated user isolation
      - Source of truth: user's PostgreSQL pantry items
      - Empty pantry check (400 EMPTY_PANTRY)
      - Expiration prioritization
      - Deterministic SHA-256 caching
      - One-shot retry & error recovery
      - Per-user rate limiting
    """
    # 1. Enforce per-user rate limit
    suggestions_rate_limiter.check(current_user.id)

    # 2. Retrieve pantry items belonging strictly to the authenticated user
    stmt = (
        select(PantryItem)
        .options(joinedload(PantryItem.ingredient))
        .where(PantryItem.user_id == current_user.id)
    )
    pantry_records = list(db.scalars(stmt).all())

    # 3. Handle empty pantry
    if not pantry_records:
        raise EmptyPantryException()

    # 4. Compute deterministic cache hash
    cache_hash = compute_recipe_cache_hash(
        user_id=current_user.id,
        meal_type=payload.meal_type,
        servings=payload.servings,
        pantry_items=pantry_records,
    )

    # 5. Check cache in database
    cached_recipes = get_cached_recipes(
        db=db,
        user_id=current_user.id,
        cache_hash=cache_hash,
    )
    if cached_recipes:
        logger.info(
            "Recipe cache hit | user_id=%d cache_hash=%s",
            current_user.id,
            cache_hash[:8],
        )
        log_llm_telemetry(
            user_id=current_user.id,
            request_id=str(uuid.uuid4()),
            model_name="cache",
            input_tokens=0,
            output_tokens=0,
            latency_ms=1.0,
            status="success",
            from_cache=True,
        )
        return cached_recipes

    # 6. Transform DB records to LLM input contracts
    pantry_inputs = [
        PantryItemInput(
            name=item.ingredient.name,
            quantity=item.quantity,
            unit=item.unit,
            expiry_date=item.expiry_date,
        )
        for item in pantry_records
        if item.ingredient
    ]

    # 7. Call LLM service
    request_id = str(uuid.uuid4())
    llm_service = get_llm_service()

    try:
        generated_recipes = await llm_service.generate_recipes(
            pantry_items=pantry_inputs,
            meal_type=payload.meal_type,
            servings=payload.servings,
            user_id=current_user.id,
            request_id=request_id,
        )
    except LLMTimeout as err:
        logger.warning("LLM call timed out for user_id=%d: %s", current_user.id, err)
        raise LLMTimeoutException() from err
    except LLMInvalidResponse as err:
        logger.error("LLM generated invalid response for user_id=%d: %s", current_user.id, err)
        raise InvalidLLMResponseException() from err
    except Exception as err:
        logger.exception("Unexpected LLM provider error for user_id=%d: %s", current_user.id, err)
        raise LLMProviderException() from err

    # 8. Persist validated recipes in PostgreSQL with cache hash
    saved_recipes = save_recipes_to_db(
        db=db,
        user_id=current_user.id,
        recipes=generated_recipes,
        cache_hash=cache_hash,
    )

    return saved_recipes
