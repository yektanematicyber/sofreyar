from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.pantry_item import utc_now_naive

# Native JSONB in PostgreSQL, standard JSON in SQLite
JSON_TYPE = JSON().with_variant(JSONB, "postgresql")


class Recipe(Base):
    """SQLAlchemy model representing a saved AI-generated or cached meal recipe."""

    __tablename__ = "recipes"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    emoji: Mapped[str] = mapped_column(String(10), nullable=False, default="🍽️")
    cooking_time: Mapped[int] = mapped_column(Integer, nullable=False)
    difficulty: Mapped[str] = mapped_column(String(20), nullable=False)
    servings: Mapped[int] = mapped_column(Integer, nullable=False)

    # Structured details stored as JSON/JSONB
    ingredients: Mapped[list[dict[str, Any]]] = mapped_column(JSON_TYPE, nullable=False)
    uses: Mapped[list[str]] = mapped_column(JSON_TYPE, nullable=False)
    missing: Mapped[list[str]] = mapped_column(JSON_TYPE, nullable=False)
    steps: Mapped[list[str]] = mapped_column(JSON_TYPE, nullable=False)
    nutrition: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, nullable=False)

    # Deterministic cache hash (indexed for rapid cache lookup)
    cache_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now_naive,
        nullable=False,
        index=True,
    )

    user: Mapped["User"] = relationship("User", back_populates="recipes")
