"""考试与作答模型：ExamRecord / Question / StudentAnswer。"""
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
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
    AuditStatus,
    BarrierType,
    Difficulty,
    ExamType,
    QuestionSource,
)
from backend.app.models.mixins import TimestampMixin


class ExamRecord(TimestampMixin, Base):
    """考试记录：一次考试一条（月考影响学情报告，练习影响 ZPD）。"""

    __tablename__ = "exam_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str | None] = mapped_column(String(128))
    class_id: Mapped[int] = mapped_column(
        ForeignKey("classes.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    teacher_id: Mapped[int | None] = mapped_column(
        ForeignKey("teachers.id", ondelete="SET NULL"), index=True
    )
    exam_type: Mapped[ExamType] = mapped_column(
        sqlite_enum(ExamType, name="exam_type"), nullable=False
    )
    exam_date: Mapped[datetime | None] = mapped_column(DateTime)
    total_score: Mapped[float | None] = mapped_column(Float)
    average_score: Mapped[float | None] = mapped_column(Float)
    # 错题统计 JSON：各题错误数据/高错误率知识点排行/班级平均分
    statistics: Mapped[dict | None] = mapped_column(JSON)


class Question(TimestampMixin, Base):
    """题目（AI 生成/手动/每日练习/OCR 入库统一结构）。"""

    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    stem: Mapped[str] = mapped_column(Text, nullable=False)          # 题干
    question_type: Mapped[str | None] = mapped_column(String(32))    # single_choice 等
    options: Mapped[list | None] = mapped_column(JSON)               # 选项列表
    answer: Mapped[str | None] = mapped_column(Text)                 # 参考答案
    explanation: Mapped[str | None] = mapped_column(Text)            # 解析
    difficulty: Mapped[Difficulty] = mapped_column(
        sqlite_enum(Difficulty, name="question_difficulty"), nullable=False
    )
    source: Mapped[QuestionSource] = mapped_column(
        sqlite_enum(QuestionSource, name="question_source"),
        default=QuestionSource.AI, server_default=QuestionSource.AI.value, nullable=False,
    )
    audit_status: Mapped[AuditStatus] = mapped_column(
        sqlite_enum(AuditStatus, name="question_audit_status"),
        default=AuditStatus.PASSED, server_default=AuditStatus.PASSED.value, nullable=False,
    )
    knowledge_point_ids: Mapped[list | None] = mapped_column(JSON)
    related_concept: Mapped[str | None] = mapped_column(String(128))
    related_reaction: Mapped[str | None] = mapped_column(String(128))
    # 四维安全审核报告 JSON（blocked 题目不可下发学生）
    audit_report: Mapped[dict | None] = mapped_column(JSON)
    review_comment: Mapped[str | None] = mapped_column(Text)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("teachers.id", ondelete="SET NULL"), index=True
    )


class StudentAnswer(TimestampMixin, Base):
    """学生作答：学生 × 题目 × 考试（练习场景 exam_record_id 可空）。"""

    __tablename__ = "student_answers"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), index=True, nullable=False
    )
    question_id: Mapped[int] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    exam_record_id: Mapped[int | None] = mapped_column(
        ForeignKey("exam_records.id", ondelete="SET NULL"), index=True
    )
    answer_text: Mapped[str | None] = mapped_column(Text)
    is_correct: Mapped[bool | None] = mapped_column(Boolean)
    barrier_type: Mapped[BarrierType | None] = mapped_column(
        sqlite_enum(BarrierType, name="answer_barrier_type")
    )
    error_type: Mapped[str | None] = mapped_column(String(64))
    consecutive_error_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0"
    )
    consecutive_correct_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0"
    )
    answered_at: Mapped[datetime | None] = mapped_column(DateTime)
