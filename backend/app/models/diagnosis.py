"""诊断与学习模型：BarrierConfig / KnowledgePoint / ReviewTask / WarningLog。"""
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, sqlite_enum
from backend.app.models.enums import (
    ReviewTaskStatus,
    WarningLevel,
    WarningType,
)
from backend.app.models.mixins import TimestampMixin


class BarrierConfig(TimestampMixin, Base):
    """教师级诊断配置（一师一份）。"""

    __tablename__ = "barrier_configs"

    id: Mapped[int] = mapped_column(primary_key=True)
    teacher_id: Mapped[int] = mapped_column(
        ForeignKey("teachers.id", ondelete="CASCADE"), unique=True, index=True,
        nullable=False,
    )
    concept_threshold: Mapped[int] = mapped_column(Integer, default=3, server_default="3")
    reading_threshold: Mapped[int] = mapped_column(Integer, default=2, server_default="2")
    expression_threshold: Mapped[int] = mapped_column(Integer, default=3, server_default="3")
    mastery_threshold: Mapped[int] = mapped_column(Integer, default=3, server_default="3")
    auto_sync: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")


class KnowledgePoint(TimestampMixin, Base):
    """知识点节点（名称/分类/PubChem 编号/关联题目数/动态错误率）。"""

    __tablename__ = "knowledge_points"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    category: Mapped[str | None] = mapped_column(String(64))
    pubchem_id: Mapped[str | None] = mapped_column(String(64))
    related_question_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0"
    )
    dynamic_error_rate: Mapped[float | None] = mapped_column(Float)


class ReviewTask(TimestampMixin, Base):
    """间隔复习任务（级别 0-5，5 不再安排；复习历史 JSON）。"""

    __tablename__ = "review_tasks"
    __table_args__ = (
        CheckConstraint("level BETWEEN 0 AND 5", name="level_range"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), index=True, nullable=False
    )
    question_id: Mapped[int] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    level: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    status: Mapped[ReviewTaskStatus] = mapped_column(
        sqlite_enum(ReviewTaskStatus, name="review_task_status"),
        default=ReviewTaskStatus.DUE, server_default=ReviewTaskStatus.DUE.value,
        nullable=False,
    )
    review_history: Mapped[list | None] = mapped_column(JSON)
    next_review_at: Mapped[datetime | None] = mapped_column(DateTime, index=True)


class WarningLog(TimestampMixin, Base):
    """学情预警（四类型 × 三级别，三通知状态标记）。"""

    __tablename__ = "warning_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), index=True, nullable=False
    )
    warning_type: Mapped[WarningType] = mapped_column(
        sqlite_enum(WarningType, name="warning_type"), nullable=False
    )
    level: Mapped[WarningLevel] = mapped_column(
        sqlite_enum(WarningLevel, name="warning_level"),
        default=WarningLevel.WARNING, server_default=WarningLevel.WARNING.value,
        nullable=False,
    )
    message: Mapped[str | None] = mapped_column(Text)
    notified_teacher: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="0"
    )
    notified_parent: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="0"
    )
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
