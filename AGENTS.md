# Safreyar Backend Agent Instructions

Welcome to the **Safreyar Backend** repository. Safreyar is a smart food, pantry, and meal planning application backend built with FastAPI, PostgreSQL 17, SQLAlchemy 2.0, Pydantic V2, Docker, and Pytest.

## 1. Quick Technical Reference

- **Language:** Python 3.12 (`python:3.12-slim`)
- **Web Framework:** FastAPI (`fastapi==0.162.0`)
- **Database & ORM:** PostgreSQL 17, SQLAlchemy 2.0 (`SQLAlchemy==2.0.55`), Alembic (`alembic==1.20.1`)
- **Validation:** Pydantic V2 (`pydantic==2.14.1`)
- **Auth:** JWT (`PyJWT==2.15.1`) with HMAC-SHA256, bcrypt (`bcrypt==5.0.0`)
- **Containerization:** Docker & Docker Compose (`docker-compose.yml`, `Dockerfile`)
- **Testing:** Pytest (`pytest==9.2.0`), HTTPX (`httpx==0.28.1`)
- **API Documentation:** `http://localhost:8001/docs` (Swagger UI)

## 2. Directory Structure

```text
safreyar-backend/
├── .agent/
│   ├── rules/
│   │   └── backend-guidelines.md
│   └── skills/
│       ├── fastapi-pro/
│       ├── python-pro/
│       ├── backend-architect/
│       ├── database-architect/
│       ├── unit-testing-test-generate/
│       ├── backend-security-coder/
│       ├── docker-pro/
│       └── safreyar-ai-meal-planner/
├── alembic/                # Database migrations
├── app/
│   ├── models/             # SQLAlchemy 2.0 models (User, Ingredient, PantryItem)
│   ├── routers/            # FastAPI route handlers (auth, ingredients, pantry)
│   ├── schemas/            # Pydantic V2 request & response schemas
│   ├── auth.py             # Security & token utilities
│   ├── database.py         # DB connection & sessionmaker
│   ├── dependencies.py     # Injected dependencies (get_current_user, get_db)
│   ├── main.py             # FastAPI entrypoint & lifespan
│   └── seed.py             # 105 seeded Persian ingredients
├── tests/                  # Pytest test suite
├── API_CONTRACT.md         # Official API contract specification
├── docker-compose.yml      # Multi-container orchestration
└── Dockerfile              # Container definition
```

## 3. Installed Workspace Skills

The following Antigravity skills are active in `.agent/skills/`:

| Skill | Focus |
|---|---|
| `fastapi-pro` | Asynchronous routes, Pydantic V2 schemas, dependency injection, and OpenAPI 3.1 |
| `python-pro` | Python 3.12 modern type hints, async execution, clean code standards |
| `backend-architect` | 3-tier layering (Routers $\to$ Services $\to$ Repositories), clean domain models |
| `database-architect` | PostgreSQL 17 tuning, SQLAlchemy 2.0 queries, Alembic migration workflows |
| `unit-testing-test-generate` | Pytest fixtures, test client isolation, and test suite generation |
| `backend-security-coder` | OWASP API Top 10, JWT lifecycle hardening, and bcrypt security |
| `docker-pro` | Dockerfile multi-stage builds, compose orchestration, and emulator networking |
| `safreyar-ai-meal-planner` | Roadmap AI features: meal suggestions, recipes, and nutrition analysis |
