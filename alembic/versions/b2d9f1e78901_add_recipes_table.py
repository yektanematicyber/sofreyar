"""add recipes table

Revision ID: b2d9f1e78901
Revises: fae8fef64966
Create Date: 2026-11-19 14:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "b2d9f1e78901"
down_revision: Union[str, Sequence[str], None] = "fae8fef64966"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

json_type = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "recipes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("emoji", sa.String(length=10), nullable=False, server_default="🍽️"),
        sa.Column("cooking_time", sa.Integer(), nullable=False),
        sa.Column("difficulty", sa.String(length=20), nullable=False),
        sa.Column("servings", sa.Integer(), nullable=False),
        sa.Column("ingredients", json_type, nullable=False),
        sa.Column("uses", json_type, nullable=False),
        sa.Column("missing", json_type, nullable=False),
        sa.Column("steps", json_type, nullable=False),
        sa.Column("nutrition", json_type, nullable=False),
        sa.Column("cache_hash", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_recipes_id"), "recipes", ["id"], unique=False)
    op.create_index(op.f("ix_recipes_user_id"), "recipes", ["user_id"], unique=False)
    op.create_index(op.f("ix_recipes_cache_hash"), "recipes", ["cache_hash"], unique=False)
    op.create_index(op.f("ix_recipes_created_at"), "recipes", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_recipes_created_at"), table_name="recipes")
    op.drop_index(op.f("ix_recipes_cache_hash"), table_name="recipes")
    op.drop_index(op.f("ix_recipes_user_id"), table_name="recipes")
    op.drop_index(op.f("ix_recipes_id"), table_name="recipes")
    op.drop_table("recipes")
