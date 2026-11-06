---
name: python-pro
description: Advanced Python 3.12+ engineering skill for Safreyar Backend. Enforces modern type hinting, asynchronous coroutine design, clean code architecture, PEP-8 compliance, and high performance.
---

# Python Pro: Safreyar Backend Engineering Standards

This skill provides expert Python engineering guidelines tailored for Python 3.12+ in `safreyar-backend`.

## 1. Python 3.12 Language Features

* **Built-in Generics:** Use `list[T]`, `dict[K, V]`, `set[T]`, `tuple[T, ...]` instead of legacy `typing.List`, `typing.Dict`.
* **Union Syntax:** Always use `A | B` and `T | None` instead of `typing.Union[A, B]` or `typing.Optional[T]`.
* **Pattern Matching:** Prefer `match / case` for multi-branch state machines, parser tokens, or response dispatching over cascading `if/elif/else`.
* **Type Aliases:** Use PEP 695 `type Name = ...` syntax for clean domain aliases.

---

## 2. Asynchronous vs Synchronous Programming Guidelines

In `safreyar-backend`, understanding the execution model is critical:

1. **CPU-bound / Cryptographic Operations (e.g. `bcrypt.hashpw`):**
   * Hashing passwords with bcrypt is CPU-intensive. When invoked inside `async def` functions, use `anyio.to_thread.run_sync` to offload to a worker thread:
     ```python
     import anyio
     hashed = await anyio.to_thread.run_sync(hash_password, plain_password)
     ```
2. **Synchronous DB Drivers (`psycopg2-binary`):**
   * The current stack uses synchronous `psycopg2-binary` with synchronous SQLAlchemy sessions (`SessionLocal`). Route handlers performing DB calls should be declared with standard `def` (allowing FastAPI's threadpool to handle blocking I/O) rather than `async def`.

---

## 3. Clean Code & Project Idioms

### Project Directory Layout:
```text
app/
├── models/         # SQLAlchemy declarative ORM models
├── routers/        # FastAPI route definitions
├── schemas/        # Pydantic V2 validation and response models
├── auth.py         # Password hashing and JWT generation
├── database.py     # Engine, sessionmaker, and Base
├── dependencies.py # Reusable FastAPI dependencies
├── main.py         # App factory, middleware, and lifespan
└── seed.py         # Database seeding routines (e.g. 105 default ingredients)
```

### Module Import Discipline:
* Always use absolute project imports:
  ```python
  from app.database import get_db
  from app.models.ingredient import Ingredient
  from app.schemas.auth import UserRegister
  ```
* Avoid relative imports (`from ..models import ...`) in application code.
* Avoid circular imports by separating ORM models into dedicated files under `app/models/` and importing base declarations cleanly.

For a comprehensive guide to modern typing patterns, see [references/type-system.md](file:///c:/Users/Lenovo/Documents/safreyar-backend/.agent/skills/python-pro/references/type-system.md).
