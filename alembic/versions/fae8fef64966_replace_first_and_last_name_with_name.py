"""replace first and last name with name

Revision ID: fae8fef64966
Revises: 4f546f9876c1
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "fae8fef64966"
down_revision: Union[str, Sequence[str], None] = "4f546f9876c1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add the new column temporarily as nullable
    op.add_column(
        "users",
        sa.Column("name", sa.String(length=200), nullable=True),
    )

    # Preserve existing users' names
    op.execute("""
        UPDATE users
        SET name = TRIM(first_name || ' ' || last_name)
    """)

    # Make name required
    op.alter_column(
        "users",
        "name",
        existing_type=sa.String(length=200),
        nullable=False,
    )

    # Remove old columns
    op.drop_column("users", "first_name")
    op.drop_column("users", "last_name")


def downgrade() -> None:
    # Restore old columns
    op.add_column(
        "users",
        sa.Column("first_name", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("last_name", sa.String(length=100), nullable=True),
    )

    # Split the full name into first and last name
    op.execute("""
        UPDATE users
        SET
            first_name = SPLIT_PART(name, ' ', 1),
            last_name = CASE
                WHEN POSITION(' ' IN name) > 0
                THEN SUBSTRING(name FROM POSITION(' ' IN name) + 1)
                ELSE ''
            END
    """)

    op.alter_column(
        "users",
        "first_name",
        existing_type=sa.String(length=100),
        nullable=False,
    )
    op.alter_column(
        "users",
        "last_name",
        existing_type=sa.String(length=100),
        nullable=False,
    )

    op.drop_column("users", "name")