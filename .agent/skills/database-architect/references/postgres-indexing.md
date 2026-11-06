# PostgreSQL 17 Indexing and Query Performance

## 1. Indexing Checklist for Safreyar

| Table | Column(s) | Index Type | Purpose |
|---|---|---|---|
| `users` | `email` | UNIQUE B-Tree | Fast lookup during login & registration check |
| `ingredients` | `name` | UNIQUE B-Tree | Exact match lookup & duplicate prevention |
| `ingredients` | `name` | GIN (`gin_trgm_ops`) | Substring & fuzzy search (`ILIKE '%query%'`) |
| `pantry_items` | `user_id` | B-Tree | Filtering items owned by current user |
| `pantry_items` | `(user_id, ingredient_id)` | UNIQUE Composite B-Tree | Enforce 1 pantry entry per ingredient per user |
| `pantry_items` | `expiry_date` | B-Tree | Sorting by nearest expiration date |

---

## 2. Implementing Trigram Index in Alembic

To add the `pg_trgm` extension and index inside an Alembic migration:

```python
from alembic import op
import sqlalchemy as sa

def upgrade() -> None:
    # Enable extension
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
    # Add GIN index
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_ingredients_name_trgm "
        "ON ingredients USING gin (name gin_trgm_ops);"
    )

def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_ingredients_name_trgm;")
```
