---
name: unit-testing-test-generate
description: Testing and QA engineering skill for Safreyar Backend. Specializes in Pytest test generation, isolated SQLite fixtures, avoiding real-database lifespan deadlocks, mock factories, and comprehensive API coverage.
---

# Unit Testing & Test Generation: Safreyar Backend Pytest Guide

This skill provides expert test engineering practices for FastAPI, SQLAlchemy, and Pytest in `safreyar-backend`.

## 1. The Core Architecture of Fast, Isolated Tests

In `safreyar-backend`, all tests must run with 100% database isolation without requiring a live PostgreSQL instance or network connectivity:

### Key Principles:
1. **In-Memory SQLite Engine:** Tests use `sqlite://` with `StaticPool` and `connect_args={"check_same_thread": False}`.
2. **Preventing Lifespan Database Deadlocks:**
   * In newer versions of FastAPI / Starlette, instantiating `TestClient(app)` or sending requests triggers the ASGI `lifespan` handler.
   * If `lifespan` contains `Base.metadata.create_all(bind=engine)`, it will attempt to connect to the external PostgreSQL database (`DATABASE_URL` in `.env`), causing tests to hang on connection timeouts!
   * **Solution:** In test configuration, either mock out the lifespan or run tests against an app instance configured with the test engine.

---

## 2. Reusable Test Fixtures (`tests/conftest.py`)

A production-grade `conftest.py` should provide clean fixtures:

```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app

@pytest.fixture
def test_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()

@pytest.fixture
def db_session(test_engine):
    TestingSessionLocal = sessionmaker(
        bind=test_engine,
        autoflush=False,
        autocommit=False,
    )
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture
def client(test_engine):
    TestingSessionLocal = sessionmaker(
        bind=test_engine,
        autoflush=False,
        autocommit=False,
    )

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=True) as test_client:
        yield test_client
    app.dependency_overrides.clear()
```

---

## 3. Test Coverage Requirements

Every endpoint in `API_CONTRACT.md` must be covered by at least 4 test cases:
1. **Happy Path:** Valid inputs produce expected HTTP status (`200 OK` or `201 Created`) and payload structure.
2. **Validation Failure:** Invalid body or query parameters return `422 Unprocessable Entity`.
3. **Authentication Failure:** Protected endpoints called without Bearer tokens return `401 Unauthorized`.
4. **Authorization / Ownership:** Accessing or deleting an item belonging to another user returns `404 Not Found` (preventing ID enumeration).

For complete fixture factories and test templates, see [references/fastapi-pytest-patterns.md](file:///c:/Users/Lenovo/Documents/safreyar-backend/.agent/skills/unit-testing-test-generate/references/fastapi-pytest-patterns.md).
