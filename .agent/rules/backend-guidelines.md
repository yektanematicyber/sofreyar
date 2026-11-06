# Safreyar Backend Engineering Rules & Guidelines

These rules apply to all AI agent interactions and code modifications within `safreyar-backend`.

## 1. Stack & Conventions
* **FastAPI:** Always use FastAPI `>=0.115.0` conventions, `APIRouter`, Pydantic V2 schemas, and dependency injection (`Depends`).
* **Python 3.12:** Use modern native types (`list[T]`, `X | None`), avoid deprecated `typing` constructs.
* **Database:** PostgreSQL 17 + SQLAlchemy 2.0. Always use modern `select()` syntax rather than `db.query()`.
* **Migrations:** All database changes must be managed via Alembic migrations under `alembic/versions/`. Never rely on `create_all` in production.
* **Testing:** Pytest with SQLite in-memory fixtures. Never allow test runs to connect to external databases or block on unmocked network/lifespan calls.
* **Security:** Follow OWASP API Security guidelines. Never expose plain text passwords or sensitive tokens. Validate resource ownership (`user_id == current_user.id`) for all item operations.

## 2. Active Skills in this Workspace
* `fastapi-pro`: For FastAPI endpoints, routers, and Pydantic schemas.
* `python-pro`: For Python 3.12 idioms, async coroutines, and typing.
* `backend-architect`: For service-repository layering and domain architecture.
* `database-architect`: For PostgreSQL 17, Alembic migrations, and indexing.
* `unit-testing-test-generate`: For Pytest fixtures, test generation, and isolation.
* `backend-security-coder`: For JWT auth, bcrypt password security, and OWASP.
* `docker-pro`: For Dockerfile, compose services, and mobile emulator networking.
* `safreyar-ai-meal-planner`: For roadmap AI meal planning, recipes, and nutrition.
