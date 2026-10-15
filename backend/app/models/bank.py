"""题库模型：QuestionSet / QuestionSetItem / HistoricalExam / HistoricalQuestion。"""
from sqlalchemy import (
    JSON,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base
from backend.app.models.mixins import TimestampMixin


class QuestionSet(TimestampMixin, Base):
    """真题集（手动整理的题目集合）。"""

    __tablename__ = "question_sets"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    source_region: Mapped[str | None] = mapped_column(String(64))  # 来源地区
    year: Mapped[int | None] = mapped_column(Integer)
    source_description: Mapped[str | None] = mapped_column(Text)  # 来源说明


class QuestionSetItem(TimestampMixin, Base):
    """真题集-题目关联（多对多，带排序）。"""

    __tablename__ = "question_set_items"
    __table_args__ = (
        UniqueConstraint("set_id", "question_id", name="set_question"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    set_id: Mapped[int] = mapped_column(
        ForeignKey("question_sets.id", ondelete="CASCADE"), index=True, nullable=False
    )
    question_id: Mapped[int] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")


class HistoricalExam(TimestampMixin, Base):
    """历年真题卷（RAG 知识底座）。"""

    __tablename__ = "historical_exams"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str | None] = mapped_column(String(128))
    source: Mapped[str | None] = mapped_column(String(128))   # 试卷来源
    region: Mapped[str | None] = mapped_column(String(64))
    year: Mapped[int | None] = mapped_column(Integer, index=True)


class HistoricalQuestion(TimestampMixin, Base):
    """历年真题题目（题号/知识点标签/难度/区分度/正文/答案/解析）。"""

    __tablename__ = "historical_questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    exam_id: Mapped[int] = mapped_column(
        ForeignKey("historical_exams.id", ondelete="CASCADE"), index=True,
        nullable=False,
    )
    question_no: Mapped[str | None] = mapped_column(String(16))
    knowledge_point_ids: Mapped[list | None] = mapped_column(JSON)
    difficulty: Mapped[float | None] = mapped_column(Float)       # 难度系数 0-1
    discrimination: Mapped[float | None] = mapped_column(Float)  # 区分度
    stem: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str | None] = mapped_column(Text)
    explanation: Mapped[str | None] = mapped_column(Text)
