# FastAPI Pytest Patterns Reference

## 1. Authenticated User Fixture Factory

Generate pre-authenticated test clients effortlessly:

```python
import pytest
from app.models.user import User
from app.auth import hash_password, create_access_token

@pytest.fixture
def auth_user(db_session):
    user = User(
        name="Test User",
        email="user@test.com",
        hashed_password=hash_password("Password123"),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def auth_headers(auth_user):
    token = create_access_token(user_id=auth_user.id)
    return {"Authorization": f"Bearer {token}"}
```

### Usage in Endpoint Tests:
```python
def test_add_pantry_item_success(client, auth_headers, db_session):
    # Setup prerequisite ingredient
    ingredient = Ingredient(name="سیب", category="میوه", default_unit="کیلوگرم")
    db_session.add(ingredient)
    db_session.commit()

    payload = {
        "ingredient_id": ingredient.id,
        "quantity": 2.5,
        "unit": "کیلوگرم",
        "expiry_date": "2026-11-20"
    }

    response = client.post("/pantry", json=payload, headers=auth_headers)

    assert response.status_code == 201
    data = response.json()
    assert data["ingredient_id"] == ingredient.id
    assert data["quantity"] == 2.5
    assert data["ingredient"]["name"] == "سیب"
```

---

## 2. Running Tests Command Reference

```powershell
# Run the entire test suite via the local venv python module
.\.venv\Scripts\python.exe -m pytest

# Run tests with verbose output
.\.venv\Scripts\python.exe -m pytest -v

# Run a specific test file
.\.venv\Scripts\python.exe -m pytest tests/test_auth.py -v

# Run with coverage report
.\.venv\Scripts\python.exe -m pytest --cov=app tests/
```
