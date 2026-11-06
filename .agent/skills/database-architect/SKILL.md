---
name: database-architect
description: PostgreSQL 17 and SQLAlchemy 2.0 database architecture skill for Safreyar Backend. Covers schema modeling, Alembic zero-downtime migrations, Persian text search indexing, connection pooling, and transactional integrity.
---

# Database Architect: Safreyar PostgreSQL & SQLAlchemy Guide

This skill provides expert database engineering guidance for PostgreSQL 17, SQLAlchemy 2.0, and Alembic in `safreyar-backend`.

## 1. SQLAlchemy 2.0 Modern Standards

Avoid legacy 1.x query idioms (`db.query(...)`). Adopt modern 2.0 `select()` and `scalars()` syntax:

```python
from sqlalchemy import select
from app.models.ingredient import Ingredient

# Modern SQLAlchemy 2.0 syntax
stmt = (
    select(Ingredient)
    .where(Ingredient.name.ilike(f"%{query}%"))
    .order_by(Ingredient.name)
    .limit(limit)
)
ingredients = db.scalars(stmt).all()
```

### Joining and Eager Loading:
When loading `PantryItem` with its related `Ingredient`, prevent N+1 query performance penalties using `selectinload` or `joinedload`:

```python
from sqlalchemy.orm import selectinload
from app.models.pantry_item import PantryItem

stmt = (
    select(PantryItem)
    .where(PantryItem.user_id == user_id)
    .options(selectinload(PantryItem.ingredient))
)
items = db.scalars(stmt).all()
```

---

## 2. Connection Pool Tuning

PostgreSQL connections in `app/database.py` should be tuned for concurrent API load and Docker networking:

```python
from sqlalchemy import create_engine

engine = create_engine(
    DATABASE_URL,
    pool_size=10,          # Standard persistent connection pool size
    max_overflow=20,       # Bursts allowed during peak requests
    pool_timeout=30,       # Timeout in seconds before raising TimeoutError
    pool_recycle=1800,     # Recycle connections after 30 minutes to prevent stale sockets
    pool_pre_ping=True,    # Test connection health before handing to requests
)
```

---

## 3. Persian Text Search & Indexing Strategies

Safreyar's ingredients database currently contains 105 seeded items primarily in Persian (e.g., `گوجه فرنگی`, `خیار`, `سیب زمینی`).
Standard B-Tree indexes on `name` only speed up exact prefix matches (`LIKE 'گوجه%'`), but `LIKE '%گوجه%'` requires full table scans.

### Optimization Strategy:
1. For sub-string and typo-tolerant search in Persian, enable `pg_trgm` (PostgreSQL Trigram Extension):
   ```sql
   CREATE EXTENSION IF NOT EXISTS pg_trgm;
   CREATE INDEX idx_ingredients_name_trgm ON ingredients USING gin (name gin_trgm_ops);
   ```
2. Keep an index on foreign keys (`user_id`, `ingredient_id` in `pantry_items`) and sort fields (`expiry_date`).

---

## 4. Alembic Migration Rules

* Never modify the database schema directly via `psql` or `Base.metadata.create_all()` in production.
* Every model change must be accompanied by a generated, reviewed, and tested Alembic revision.
* Always check and verify both `upgrade()` and `downgrade()` functions.

For the step-by-step migration playbook, see [references/alembic-workflows.md](file:///c:/Users/Lenovo/Documents/safreyar-backend/.agent/skills/database-architect/references/alembic-workflows.md).
For indexing best practices, see [references/postgres-indexing.md](file:///c:/Users/Lenovo/Documents/safreyar-backend/.agent/skills/database-architect/references/postgres-indexing.md).
