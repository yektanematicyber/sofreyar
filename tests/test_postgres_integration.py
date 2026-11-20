import os
from sqlalchemy import create_engine
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

import pytest
from app.models.recipe import Recipe


def test_postgres_table_compilation_uses_jsonb():
    """Verifies that the Recipe table definition compiles JSONB columns under the PostgreSQL dialect."""
    pg_dialect = postgresql.dialect()
    ddl = str(CreateTable(Recipe.__table__).compile(dialect=pg_dialect))

    # Verify JSONB is generated for json-based fields
    assert "ingredients JSONB" in ddl
    assert "uses JSONB" in ddl
    assert "missing JSONB" in ddl
    assert "steps JSONB" in ddl
    assert "nutrition JSONB" in ddl

    # Verify foreign key constraint
    assert "FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE" in ddl


def test_postgres_indexes_compilation():
    """Verifies that indexes on user_id and cache_hash are present in table metadata."""
    indexes = {idx.name: idx for idx in Recipe.__table__.indexes}

    assert "ix_recipes_user_id" in indexes
    assert "ix_recipes_cache_hash" in indexes

    user_id_cols = [c.name for c in indexes["ix_recipes_user_id"].columns]
    assert user_id_cols == ["user_id"]

    cache_hash_cols = [c.name for c in indexes["ix_recipes_cache_hash"].columns]
    assert cache_hash_cols == ["cache_hash"]


def test_live_postgres_integration_if_configured():
    """Optional live PostgreSQL integration test when TEST_DATABASE_URL is provided."""
    test_pg_url = os.getenv("TEST_DATABASE_URL")
    if not test_pg_url:
        pytest.skip("TEST_DATABASE_URL not set; skipping live PostgreSQL test")

    engine = create_engine(test_pg_url)
    with engine.connect() as conn:
        result = conn.execute(Recipe.__table__.select().limit(1))
        assert result is not None
