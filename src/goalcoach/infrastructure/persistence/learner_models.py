"""SQLAlchemy ORM model for learner aggregate snapshots."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class LearnerBase(DeclarativeBase):
    """Base declarative class for the learner state database."""


class LearnerStateORM(LearnerBase):
    """Stores full aggregate state snapshots of learners."""

    __tablename__ = "learner_states"

    learner_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    state_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
