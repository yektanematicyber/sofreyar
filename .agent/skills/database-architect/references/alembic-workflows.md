# Alembic Migration Workflow Reference: Safreyar Backend

## 1. Step-by-Step Migration Lifecycle

When changing or adding SQLAlchemy models in `app/models/`:

### Step 1: Ensure Model is Registered in Alembic
In `alembic/env.py`, ensure `target_metadata` imports and registers all model files:
```python
from app.database import Base
from app import models  # Imports user, ingredient, pantry_item, etc.

target_metadata = Base.metadata
```

### Step 2: Generate Migration Revision
Run the revision generator with a meaningful descriptive slug:
```powershell
alembic revision --autogenerate -m "create_recipes_and_recipe_ingredients"
```

### Step 3: Review Generated Migration Script
Inspect the newly created file in `alembic/versions/`:
* Verify column types (`String`, `Integer`, `Date`, `DateTime(timezone=True)`).
* Check foreign keys and `ondelete="CASCADE"` or `ondelete="RESTRICT"` policies.
* Ensure nullable vs non-nullable flags match the intent.
* Verify that `downgrade()` properly reverts the change.

### Step 4: Apply Migration
```powershell
alembic upgrade head
```

### Step 5: Verify Migration Status
```powershell
alembic current
alembic history --verbose
```

---

## 2. Docker Execution
If running inside Docker or applying migrations in containerized environments:
```powershell
docker compose exec backend alembic upgrade head
```
Or check the current version:
```powershell
docker compose exec backend alembic current
```
