from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class CurriculumConcept(Base):
    __tablename__ = "curriculum_concepts"

    concept_id: Mapped[str] = mapped_column(String, primary_key=True)
    hsk_level: Mapped[int] = mapped_column(Integer)
    sequence_no: Mapped[int] = mapped_column(Integer, unique=True)
    slug: Mapped[str] = mapped_column(String, unique=True)
    title_zh: Mapped[str] = mapped_column(String)
    title_en: Mapped[str] = mapped_column(String)
    concept_type: Mapped[str] = mapped_column(String)
    communicative_goal: Mapped[str] = mapped_column(Text)
    grammar_focus: Mapped[list[str]] = mapped_column(JSON, default=list)
    vocabulary_focus: Mapped[list[str]] = mapped_column(JSON, default=list)
    difficulty: Mapped[int] = mapped_column(Integer, default=1)
    estimated_minutes: Mapped[int] = mapped_column(Integer, default=6)
    source_ref: Mapped[str] = mapped_column(String, default="HSK3.0-2026")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)

    teaching_cards: Mapped[list[TeachingCard]] = relationship(
        back_populates="concept", cascade="all, delete-orphan"
    )
    exercises: Mapped[list[ContentExercise]] = relationship(
        back_populates="concept", cascade="all, delete-orphan"
    )


class TeachingCard(Base):
    __tablename__ = "teaching_cards"
    __table_args__ = (UniqueConstraint("concept_id", "card_order"),)

    card_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    concept_id: Mapped[str] = mapped_column(
        ForeignKey("curriculum_concepts.concept_id", ondelete="CASCADE")
    )
    card_order: Mapped[int] = mapped_column(Integer)
    card_type: Mapped[str] = mapped_column(String)
    prompt_zh: Mapped[str | None] = mapped_column(Text)
    pinyin: Mapped[str | None] = mapped_column(Text)
    meaning_en: Mapped[str | None] = mapped_column(Text)
    explanation_en: Mapped[str | None] = mapped_column(Text)
    example_zh: Mapped[str | None] = mapped_column(Text)
    example_pinyin: Mapped[str | None] = mapped_column(Text)
    example_en: Mapped[str | None] = mapped_column(Text)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    concept: Mapped[CurriculumConcept] = relationship(back_populates="teaching_cards")


class ContentExercise(Base):
    __tablename__ = "exercises"
    __table_args__ = (UniqueConstraint("concept_id", "exercise_order"),)

    exercise_id: Mapped[str] = mapped_column(String, primary_key=True)
    concept_id: Mapped[str] = mapped_column(
        ForeignKey("curriculum_concepts.concept_id", ondelete="CASCADE")
    )
    exercise_order: Mapped[int] = mapped_column(Integer)
    exercise_type: Mapped[str] = mapped_column(String)
    prompt: Mapped[str] = mapped_column(Text)
    prompt_pinyin: Mapped[str | None] = mapped_column(Text)
    instruction: Mapped[str] = mapped_column(Text)
    answer: Mapped[dict[str, Any]] = mapped_column(JSON)
    options: Mapped[list[str] | None] = mapped_column(JSON)
    accepted_answers: Mapped[list[str]] = mapped_column(JSON, default=list)
    explanation: Mapped[str] = mapped_column(Text)
    target_tokens: Mapped[list[str]] = mapped_column(JSON, default=list)
    error_tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    difficulty: Mapped[int] = mapped_column(Integer, default=1)
    points: Mapped[int] = mapped_column(Integer, default=10)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)

    concept: Mapped[CurriculumConcept] = relationship(back_populates="exercises")


class ConceptPrerequisite(Base):
    __tablename__ = "concept_prerequisites"
    __table_args__ = (CheckConstraint("concept_id <> prerequisite_id"),)

    concept_id: Mapped[str] = mapped_column(
        ForeignKey("curriculum_concepts.concept_id", ondelete="CASCADE"), primary_key=True
    )
    prerequisite_id: Mapped[str] = mapped_column(
        ForeignKey("curriculum_concepts.concept_id", ondelete="CASCADE"), primary_key=True
    )


class LearnerStateRecord(Base):
    """Database record storing one learner's complete state as a JSON snapshot."""

    __tablename__ = "learner_states"

    learner_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    state_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
