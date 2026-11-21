from datetime import date
import logging
import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.dependencies import get_current_user
from app.exceptions import (
    DatabaseException,
    EmptyPantryException,
    InvalidLLMResponseException,
    LLMProviderException,
    LLMTimeoutException,
)
from app.llm import (
    LLMAuthenticationError,
    LLMInvalidResponse,
    LLMProviderError,
    LLMRateLimitError,
    LLMTimeout,
    PantryItemInput,
    get_llm_service,
)
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
    try:
        stmt = (
            select(PantryItem)
            .options(joinedload(PantryItem.ingredient))
            .where(PantryItem.user_id == current_user.id)
        )
        pantry_records = list(db.scalars(stmt).all())
    except SQLAlchemyError as err:
        logger.exception("Database error while fetching pantry items for user_id=%d: %s", current_user.id, err)
        raise DatabaseException() from err

    # 3. Handle empty pantry and enforce deterministic backend food safety
    if not pantry_records:
        raise EmptyPantryException()

    today = date.today()
    safe_pantry_records = [
        item for item in pantry_records
        if item.expiry_date is None or item.expiry_date >= today
    ]

    if not safe_pantry_records:
        logger.warning("All pantry items for user_id=%d are expired; rejecting for food safety", current_user.id)
        raise EmptyPantryException(
            detail="تمام مواد غذایی موجود در انبار شما منقضی شده‌اند. لطفاً مواد تازه به انبار خود اضافه کنید."
        )

    # 4. Compute deterministic cache hash based on safe pantry inventory
    cache_hash = compute_recipe_cache_hash(
        user_id=current_user.id,
        meal_type=payload.meal_type,
        servings=payload.servings,
        pantry_items=safe_pantry_records,
    )

    # 5. Check cache in database
    try:
        cached_recipes = get_cached_recipes(
            db=db,
            user_id=current_user.id,
            cache_hash=cache_hash,
        )
    except SQLAlchemyError as err:
        logger.exception("Database error while checking recipe cache for user_id=%d: %s", current_user.id, err)
        raise DatabaseException() from err

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

    # 6. Transform verified safe DB records to LLM input contracts
    pantry_inputs = [
        PantryItemInput(
            name=item.ingredient.name,
            quantity=item.quantity,
            unit=item.unit,
            expiry_date=item.expiry_date,
        )
        for item in safe_pantry_records
        if item.ingredient
    ]

    # 7. Call LLM service
    request_id = str(uuid.uuid4())
    llm_service = get_llm_service()
    model_name = getattr(getattr(llm_service, "config", None), "llm_model", "fake-persian-model")

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
    except LLMAuthenticationError as err:
        logger.error("LLM authentication failure for user_id=%d: %s", current_user.id, err)
        raise LLMProviderException(detail="خطا در احراز هویت سرویس هوش مصنوعی.") from err
    except LLMRateLimitError as err:
        logger.warning("LLM provider rate limit exceeded for user_id=%d: %s", current_user.id, err)
        raise LLMProviderException(detail="سقف مصرف ارائه‌دهنده هوش مصنوعی به پایان رسیده است.") from err
    except LLMProviderError as err:
        logger.error("LLM provider error for user_id=%d: %s", current_user.id, err)
        raise LLMProviderException() from err
    except Exception as err:
        logger.exception("Unexpected LLM provider error for user_id=%d: %s", current_user.id, err)
        log_llm_telemetry(
            user_id=current_user.id,
            request_id=request_id,
            model_name=model_name,
            input_tokens=0,
            output_tokens=0,
            latency_ms=0.0,
            status="provider_error",
        )
        raise LLMProviderException() from err

    # 8. Persist validated recipes in PostgreSQL with cache hash
    try:
        saved_recipes = save_recipes_to_db(
            db=db,
            user_id=current_user.id,
            recipes=generated_recipes,
            cache_hash=cache_hash,
        )
    except SQLAlchemyError as err:
        logger.exception("Database error while saving recipes for user_id=%d: %s", current_user.id, err)
        raise DatabaseException() from err

    return saved_recipes
