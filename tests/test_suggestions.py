import os
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app import rate_limiter
from app.exceptions import InvalidLLMResponseException, LLMTimeoutException
from app.llm.interface import LLMInvalidResponse, LLMTimeout
from app.models import Ingredient, PantryItem, Recipe, User
from app.rate_limiter import UserRateLimiter


def create_user_and_token(client, email="user@example.com", name="Test User") -> tuple[dict[str, str], int]:
    register_res = client.post(
        "/auth/register",
        json={"name": name, "email": email, "password": "Password123"},
    )
    user_id = register_res.json()["id"]

    login_res = client.post(
        "/auth/login",
        json={"email": email, "password": "Password123"},
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    return headers, user_id


def seed_ingredient(db, name="تخم‌مرغ", category="dairy", default_unit="piece") -> Ingredient:
    ing = Ingredient(name=name, category=category, default_unit=default_unit)
    db.add(ing)
    db.commit()
    db.refresh(ing)
    return ing


def add_pantry_item(db, user_id: int, ingredient_id: int, quantity: float = 4.0, unit: str = "piece", expiry_date=None) -> PantryItem:
    item = PantryItem(
        user_id=user_id,
        ingredient_id=ingredient_id,
        quantity=quantity,
        unit=unit,
        expiry_date=expiry_date,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


# ==============================================================================
# 1. Suggestions API Tests
# ==============================================================================

def test_suggestions_unauthenticated_rejected(client):
    response = client.post("/suggestions", json={"meal_type": "lunch", "servings": 2})
    assert response.status_code == 401
    assert "detail" in response.json()


def test_suggestions_empty_pantry_returns_400(client, db_session):
    headers, _ = create_user_and_token(client, email="empty_pantry@example.com")
    response = client.post("/suggestions", headers=headers, json={"meal_type": "lunch", "servings": 2})
    assert response.status_code == 400
    data = response.json()
    assert data["error_code"] == "EMPTY_PANTRY"
    assert "انبار شما خالی است" in data["detail"]


def test_suggestions_all_expired_pantry_rejected_by_business_logic(client, db_session):
    headers, user_id = create_user_and_token(client, email="expired_only@example.com")
    ing = seed_ingredient(db_session, name="شیر ترش")
    today = date.today()
    add_pantry_item(db_session, user_id, ing.id, quantity=1.0, unit="l", expiry_date=today - timedelta(days=3))

    response = client.post("/suggestions", headers=headers, json={"meal_type": "breakfast", "servings": 2})
    assert response.status_code == 400
    data = response.json()
    assert data["error_code"] == "EMPTY_PANTRY"
    assert "منقضی شده‌اند" in data["detail"]


def test_suggestions_invalid_meal_type_rejected(client, db_session):
    headers, user_id = create_user_and_token(client, email="invalid_meal@example.com")
    ing = seed_ingredient(db_session, name="نان سنگک")
    add_pantry_item(db_session, user_id, ing.id)

    response = client.post("/suggestions", headers=headers, json={"meal_type": "brunch", "servings": 2})
    assert response.status_code == 422
    data = response.json()
    assert data["error_code"] == "INVALID_REQUEST"


def test_suggestions_invalid_servings_rejected(client, db_session):
    headers, user_id = create_user_and_token(client, email="invalid_servings@example.com")
    ing = seed_ingredient(db_session, name="سیب‌زمینی")
    add_pantry_item(db_session, user_id, ing.id)

    # Servings = 0
    res_zero = client.post("/suggestions", headers=headers, json={"meal_type": "dinner", "servings": 0})
    assert res_zero.status_code == 422
    assert res_zero.json()["error_code"] == "INVALID_REQUEST"

    # Servings = -2
    res_neg = client.post("/suggestions", headers=headers, json={"meal_type": "dinner", "servings": -2})
    assert res_neg.status_code == 422
    assert res_neg.json()["error_code"] == "INVALID_REQUEST"


def test_suggestions_success_returns_three_recipes(client, db_session):
    headers, user_id = create_user_and_token(client, email="success_user@example.com")
    ing1 = seed_ingredient(db_session, name="تخم‌مرغ")
    ing2 = seed_ingredient(db_session, name="گوجه‌فرنگی")
    add_pantry_item(db_session, user_id, ing1.id, quantity=4.0, unit="piece")
    add_pantry_item(db_session, user_id, ing2.id, quantity=5.0, unit="piece")

    response = client.post("/suggestions", headers=headers, json={"meal_type": "lunch", "servings": 2})
    assert response.status_code == 200
    recipes = response.json()
    assert isinstance(recipes, list)
    assert len(recipes) == 3

    for r in recipes:
        assert r["id"] > 0
        assert r["user_id"] == user_id
        assert r["title"]
        assert r["summary"]
        assert r["emoji"]
        assert r["cooking_time"] > 0
        assert r["servings"] == 2
        assert len(r["ingredients"]) > 0
        assert len(r["steps"]) > 0
        assert r["nutrition"]["calories"] > 0


def test_suggestions_user_isolation(client, db_session):
    # User A has pantry items
    headers_a, user_a_id = create_user_and_token(client, email="user_a@example.com")
    ing = seed_ingredient(db_session, name="عدس سبز")
    add_pantry_item(db_session, user_a_id, ing.id, quantity=500.0, unit="g")

    # User B has empty pantry
    headers_b, _ = create_user_and_token(client, email="user_b@example.com")

    # User B cannot generate recipes using User A's pantry
    res_b = client.post("/suggestions", headers=headers_b, json={"meal_type": "lunch", "servings": 2})
    assert res_b.status_code == 400
    assert res_b.json()["error_code"] == "EMPTY_PANTRY"

    # User A succeeds
    res_a = client.post("/suggestions", headers=headers_a, json={"meal_type": "lunch", "servings": 2})
    assert res_a.status_code == 200
    assert len(res_a.json()) == 3


# ==============================================================================
# 2. Recipe Database & GET /recipes/{id} Tests
# ==============================================================================

def test_recipe_database_persistence_and_retrieval(client, db_session):
    headers, user_id = create_user_and_token(client, email="recipe_db@example.com")
    ing = seed_ingredient(db_session, name="سینه مرغ")
    add_pantry_item(db_session, user_id, ing.id, quantity=300.0, unit="g")

    # Generate recipes
    sug_res = client.post("/suggestions", headers=headers, json={"meal_type": "dinner", "servings": 3})
    assert sug_res.status_code == 200
    recipes = sug_res.json()
    first_recipe_id = recipes[0]["id"]

    # Retrieve by ID
    get_res = client.get(f"/recipes/{first_recipe_id}", headers=headers)
    assert get_res.status_code == 200
    rec = get_res.json()
    assert rec["id"] == first_recipe_id
    assert rec["user_id"] == user_id
    assert rec["title"] == recipes[0]["title"]
    assert rec["cooking_time"] == recipes[0]["cooking_time"]


def test_recipe_ownership_isolation(client, db_session):
    # User A generates recipe
    headers_a, user_a_id = create_user_and_token(client, email="owner_a@example.com")
    ing = seed_ingredient(db_session, name="خیار")
    add_pantry_item(db_session, user_a_id, ing.id, quantity=2.0, unit="piece")
    sug_res = client.post("/suggestions", headers=headers_a, json={"meal_type": "snack", "servings": 1})
    recipe_id = sug_res.json()[0]["id"]

    # User B tries to view User A's recipe
    headers_b, _ = create_user_and_token(client, email="viewer_b@example.com")
    get_res = client.get(f"/recipes/{recipe_id}", headers=headers_b)
    assert get_res.status_code == 404
    assert get_res.json()["error_code"] == "RECIPE_NOT_FOUND"


def test_recipe_not_found(client, db_session):
    headers, _ = create_user_and_token(client, email="notfound@example.com")
    res = client.get("/recipes/99999", headers=headers)
    assert res.status_code == 404
    assert res.json()["error_code"] == "RECIPE_NOT_FOUND"


# ==============================================================================
# 3. Cache Tests
# ==============================================================================

def test_recipe_cache_hit_on_identical_request(client, db_session):
    headers, user_id = create_user_and_token(client, email="cache_test@example.com")
    ing = seed_ingredient(db_session, name="برنج")
    add_pantry_item(db_session, user_id, ing.id, quantity=1.0, unit="kg")

    # 1st request -> generates and caches
    res1 = client.post("/suggestions", headers=headers, json={"meal_type": "lunch", "servings": 2})
    assert res1.status_code == 200
    recipes1 = res1.json()
    ids1 = [r["id"] for r in recipes1]

    # 2nd request -> identical parameters and pantry -> cache hit!
    res2 = client.post("/suggestions", headers=headers, json={"meal_type": "lunch", "servings": 2})
    assert res2.status_code == 200
    recipes2 = res2.json()
    ids2 = [r["id"] for r in recipes2]

    # Exactly same database IDs returned from cache
    assert ids1 == ids2


def test_recipe_cache_different_meal_type_invalidates_cache(client, db_session):
    headers, user_id = create_user_and_token(client, email="cache_meal@example.com")
    ing = seed_ingredient(db_session, name="لوبیا")
    add_pantry_item(db_session, user_id, ing.id, quantity=500.0, unit="g")

    res_lunch = client.post("/suggestions", headers=headers, json={"meal_type": "lunch", "servings": 2})
    ids_lunch = [r["id"] for r in res_lunch.json()]

    res_dinner = client.post("/suggestions", headers=headers, json={"meal_type": "dinner", "servings": 2})
    ids_dinner = [r["id"] for r in res_dinner.json()]

    assert ids_lunch != ids_dinner


def test_recipe_cache_changed_quantity_invalidates_cache(client, db_session):
    headers, user_id = create_user_and_token(client, email="cache_qty@example.com")
    ing = seed_ingredient(db_session, name="گردو")
    pantry_item = add_pantry_item(db_session, user_id, ing.id, quantity=100.0, unit="g")

    res1 = client.post("/suggestions", headers=headers, json={"meal_type": "breakfast", "servings": 2})
    ids1 = [r["id"] for r in res1.json()]

    # Update pantry quantity
    pantry_item.quantity = 500.0
    db_session.commit()

    res2 = client.post("/suggestions", headers=headers, json={"meal_type": "breakfast", "servings": 2})
    ids2 = [r["id"] for r in res2.json()]

    assert ids1 != ids2


def test_recipe_cache_changed_expiry_date_invalidates_cache(client, db_session):
    headers, user_id = create_user_and_token(client, email="cache_exp@example.com")
    ing = seed_ingredient(db_session, name="شیر")
    today = date.today()
    pantry_item = add_pantry_item(db_session, user_id, ing.id, quantity=1.0, unit="l", expiry_date=today + timedelta(days=7))

    res1 = client.post("/suggestions", headers=headers, json={"meal_type": "breakfast", "servings": 2})
    ids1 = [r["id"] for r in res1.json()]

    # Update expiry date (urgency changed)
    pantry_item.expiry_date = today + timedelta(days=1)
    db_session.commit()

    res2 = client.post("/suggestions", headers=headers, json={"meal_type": "breakfast", "servings": 2})
    ids2 = [r["id"] for r in res2.json()]

    assert ids1 != ids2


def test_recipe_cache_user_isolation(client, db_session):
    # User A
    headers_a, user_a_id = create_user_and_token(client, email="cache_user_a@example.com")
    ing = seed_ingredient(db_session, name="پیاز")
    add_pantry_item(db_session, user_a_id, ing.id, quantity=2.0, unit="piece")
    res_a = client.post("/suggestions", headers=headers_a, json={"meal_type": "lunch", "servings": 2})
    ids_a = [r["id"] for r in res_a.json()]

    # User B with identical pantry items
    headers_b, user_b_id = create_user_and_token(client, email="cache_user_b@example.com")
    add_pantry_item(db_session, user_b_id, ing.id, quantity=2.0, unit="piece")
    res_b = client.post("/suggestions", headers=headers_b, json={"meal_type": "lunch", "servings": 2})
    ids_b = [r["id"] for r in res_b.json()]

    # Cache is strictly user-isolated: User B gets their own recipe records
    assert ids_a != ids_b
    assert all(r["user_id"] == user_b_id for r in res_b.json())


# ==============================================================================
# 4. Rate Limiting Tests
# ==============================================================================

def test_suggestions_rate_limiter_blocks_excess(client, db_session, monkeypatch):
    from app.rate_limiter import suggestions_rate_limiter

    # Temporarily enable rate limiter with tight limit
    rate_limiter.RATE_LIMIT_ENABLED = True
    suggestions_rate_limiter.times = 2
    suggestions_rate_limiter.seconds = 60
    suggestions_rate_limiter.requests.clear()

    headers, user_id = create_user_and_token(client, email="ratelimit_user@example.com")
    ing = seed_ingredient(db_session, name="ماست")
    add_pantry_item(db_session, user_id, ing.id, quantity=300.0, unit="g")

    try:
        # Request 1: OK
        res1 = client.post("/suggestions", headers=headers, json={"meal_type": "snack", "servings": 1})
        assert res1.status_code == 200

        # Request 2: OK
        res2 = client.post("/suggestions", headers=headers, json={"meal_type": "snack", "servings": 1})
        assert res2.status_code == 200

        # Request 3: Blocked (429)
        res3 = client.post("/suggestions", headers=headers, json={"meal_type": "snack", "servings": 1})
        assert res3.status_code == 429
        data = res3.json()
        assert data["error_code"] == "RATE_LIMIT_EXCEEDED"
        assert "Retry-After" in res3.headers
    finally:
        rate_limiter.RATE_LIMIT_ENABLED = False


def test_suggestions_rate_limiter_isolated_per_user(client, db_session, monkeypatch):
    from app.rate_limiter import suggestions_rate_limiter

    rate_limiter.RATE_LIMIT_ENABLED = True
    suggestions_rate_limiter.times = 1
    suggestions_rate_limiter.seconds = 60
    suggestions_rate_limiter.requests.clear()

    headers_a, user_a = create_user_and_token(client, email="rl_a@example.com")
    headers_b, user_b = create_user_and_token(client, email="rl_b@example.com")
    ing = seed_ingredient(db_session, name="کره")
    add_pantry_item(db_session, user_a, ing.id, quantity=50.0, unit="g")
    add_pantry_item(db_session, user_b, ing.id, quantity=50.0, unit="g")

    try:
        # User A uses quota
        res_a1 = client.post("/suggestions", headers=headers_a, json={"meal_type": "breakfast", "servings": 1})
        assert res_a1.status_code == 200

        # User A blocked
        res_a2 = client.post("/suggestions", headers=headers_a, json={"meal_type": "breakfast", "servings": 1})
        assert res_a2.status_code == 429

        # User B still has quota!
        res_b1 = client.post("/suggestions", headers=headers_b, json={"meal_type": "breakfast", "servings": 1})
        assert res_b1.status_code == 200
    finally:
        rate_limiter.RATE_LIMIT_ENABLED = False


# ==============================================================================
# 5. LLM Error Mapping Tests
# ==============================================================================

def test_suggestions_llm_timeout_mapped_to_504(client, db_session, monkeypatch):
    headers, user_id = create_user_and_token(client, email="timeout_err@example.com")
    ing = seed_ingredient(db_session, name="گوجه")
    add_pantry_item(db_session, user_id, ing.id, quantity=2.0, unit="piece")

    mock_llm = AsyncMock()
    mock_llm.generate_recipes.side_effect = LLMTimeout("Model call timed out")

    monkeypatch.setattr("app.routers.suggestions.get_llm_service", lambda: mock_llm)

    res = client.post("/suggestions", headers=headers, json={"meal_type": "lunch", "servings": 2})
    assert res.status_code == 504
    data = res.json()
    assert data["error_code"] == "LLM_TIMEOUT"
    assert "بیش از حد مجاز" in data["detail"]


def test_suggestions_llm_invalid_response_mapped_to_502(client, db_session, monkeypatch):
    headers, user_id = create_user_and_token(client, email="invalid_llm_err@example.com")
    ing = seed_ingredient(db_session, name="تخم مرغ")
    add_pantry_item(db_session, user_id, ing.id, quantity=2.0, unit="piece")

    mock_llm = AsyncMock()
    mock_llm.generate_recipes.side_effect = LLMInvalidResponse("Malformed JSON output")

    monkeypatch.setattr("app.routers.suggestions.get_llm_service", lambda: mock_llm)

    res = client.post("/suggestions", headers=headers, json={"meal_type": "lunch", "servings": 2})
    assert res.status_code == 502
    data = res.json()
    assert data["error_code"] == "INVALID_LLM_RESPONSE"
    assert "ساختار معتبری نداشت" in data["detail"]


def test_suggestions_llm_provider_error_mapped_to_502(client, db_session, monkeypatch):
    headers, user_id = create_user_and_token(client, email="provider_err@example.com")
    ing = seed_ingredient(db_session, name="روغن")
    add_pantry_item(db_session, user_id, ing.id, quantity=100.0, unit="ml")

    mock_llm = AsyncMock()
    mock_llm.generate_recipes.side_effect = RuntimeError("OpenRouter connection failed")

    monkeypatch.setattr("app.routers.suggestions.get_llm_service", lambda: mock_llm)

    res = client.post("/suggestions", headers=headers, json={"meal_type": "lunch", "servings": 2})
    assert res.status_code == 502
    data = res.json()
    assert data["error_code"] == "LLM_PROVIDER_ERROR"
    assert "خطا در برقراری ارتباط" in data["detail"]


# ==============================================================================
# 6. Sprint 2 Review Regression Tests (Cache, Redis Lua, DB Errors, Sanitization)
# ==============================================================================

def test_recipe_cache_model_change_invalidates_cache(db_session):
    from app.services.recipe_cache import compute_recipe_cache_hash

    ing = seed_ingredient(db_session, name="نان سنگک")
    today = date.today()
    item = PantryItem(id=1, user_id=1, ingredient_id=ing.id, quantity=1.0, unit="piece", expiry_date=today)
    item.ingredient = ing

    hash_gemma = compute_recipe_cache_hash(
        user_id=1, meal_type="breakfast", servings=2, pantry_items=[item], model_name="google/gemma-4-26b-a4b-it:free", prompt_version="v1"
    )
    hash_llama = compute_recipe_cache_hash(
        user_id=1, meal_type="breakfast", servings=2, pantry_items=[item], model_name="meta-llama/llama-3.3-70b-instruct:free", prompt_version="v1"
    )

    assert hash_gemma != hash_llama


def test_recipe_cache_prompt_version_change_invalidates_cache(db_session):
    from app.services.recipe_cache import compute_recipe_cache_hash

    ing = seed_ingredient(db_session, name="گردو")
    item = PantryItem(id=1, user_id=1, ingredient_id=ing.id, quantity=100.0, unit="g")
    item.ingredient = ing

    hash_v1 = compute_recipe_cache_hash(
        user_id=1, meal_type="breakfast", servings=2, pantry_items=[item], model_name="google/gemma-4-26b-a4b-it:free", prompt_version="v1"
    )
    hash_v2 = compute_recipe_cache_hash(
        user_id=1, meal_type="breakfast", servings=2, pantry_items=[item], model_name="google/gemma-4-26b-a4b-it:free", prompt_version="v2"
    )

    assert hash_v1 != hash_v2


def test_redis_url_sanitization():
    from app.rate_limiter import sanitize_redis_url

    masked1 = sanitize_redis_url("redis://:mysecretpass@localhost:6379/0")
    assert masked1 == "redis://:***@localhost:6379/0"
    assert "mysecretpass" not in masked1

    masked2 = sanitize_redis_url("redis://admin:super_secret@redis.internal:6380/2")
    assert masked2 == "redis://admin:***@redis.internal:6380/2"
    assert "super_secret" not in masked2

    unmasked = sanitize_redis_url("redis://localhost:6379/0")
    assert unmasked == "redis://localhost:6379/0"


def test_redis_atomic_rate_limiter_lua_execution():
    from app.exceptions import RateLimitExceededException
    from app.rate_limiter import UserRateLimiter, RATE_LIMIT_ENABLED
    import app.rate_limiter as rate_limiter_mod

    rate_limiter_mod.RATE_LIMIT_ENABLED = True
    try:
        limiter = UserRateLimiter(times=2, seconds=60)
        mock_redis = MagicMock()
        mock_lua = MagicMock()
        mock_lua.side_effect = [
            [1, 0],   # Request 1: allowed
            [1, 0],   # Request 2: allowed
            [0, 45],  # Request 3: blocked with 45s retry
        ]
        limiter.redis_client = mock_redis
        limiter.lua_script = mock_lua

        limiter.check(user_id=999)
        limiter.check(user_id=999)

        with pytest.raises(RateLimitExceededException) as exc_info:
            limiter.check(user_id=999)

        assert exc_info.value.status_code == 429
        assert exc_info.value.headers["Retry-After"] == "45"
        assert mock_lua.call_count == 3
    finally:
        rate_limiter_mod.RATE_LIMIT_ENABLED = False


def test_redis_rate_limiter_fallback_on_error():
    from app.rate_limiter import UserRateLimiter
    import app.rate_limiter as rate_limiter_mod

    rate_limiter_mod.RATE_LIMIT_ENABLED = True
    try:
        limiter = UserRateLimiter(times=1, seconds=60)
        mock_redis = MagicMock()
        mock_lua = MagicMock()
        mock_lua.side_effect = ConnectionError("Redis is unreachable")
        limiter.redis_client = mock_redis
        limiter.lua_script = mock_lua

        # First request: Redis fails, falls back to in-memory, succeeds
        limiter.check(user_id=888)

        # Second request: Redis fails, falls back to in-memory, blocked!
        from app.exceptions import RateLimitExceededException
        with pytest.raises(RateLimitExceededException):
            limiter.check(user_id=888)
    finally:
        rate_limiter_mod.RATE_LIMIT_ENABLED = False


def test_database_error_mapped_to_500_database_error(client, db_session):
    headers, user_id = create_user_and_token(client, email="db_err_user@example.com")
    from app.database import get_db
    from sqlalchemy.exc import OperationalError

    def mock_db_with_error():
        mock_session = MagicMock()
        mock_session.scalars.side_effect = OperationalError("connection lost", {}, Exception())
        yield mock_session

    client.app.dependency_overrides[get_db] = mock_db_with_error
    try:
        res = client.post("/suggestions", headers=headers, json={"meal_type": "lunch", "servings": 2})
        assert res.status_code == 500
        data = res.json()
        assert data["error_code"] == "DATABASE_ERROR"
        assert "پایگاه داده" in data["detail"]
    finally:
        client.app.dependency_overrides.pop(get_db, None)


def test_recipe_get_database_error_mapped_to_500(client, db_session):
    headers, user_id = create_user_and_token(client, email="db_recipe_err@example.com")
    from app.database import get_db
    from sqlalchemy.exc import OperationalError

    def mock_db_with_error():
        mock_session = MagicMock()
        mock_session.get.side_effect = OperationalError("disk error", {}, Exception())
        yield mock_session

    client.app.dependency_overrides[get_db] = mock_db_with_error
    try:
        res = client.get("/recipes/123", headers=headers)
        assert res.status_code == 500
        data = res.json()
        assert data["error_code"] == "DATABASE_ERROR"
        assert "پایگاه داده" in data["detail"]
    finally:
        client.app.dependency_overrides.pop(get_db, None)
