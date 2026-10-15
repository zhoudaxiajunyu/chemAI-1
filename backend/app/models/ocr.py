"""OCR 批改模型：UploadSession / OCRTask / StudentSubmission。"""
from datetime import datetime

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, sqlite_enum
from backend.app.models.enums import OCRTaskStatus, UploadSessionStatus
from backend.app.models.mixins import TimestampMixin


# 上传会话合法状态转移（应用层状态机）
ALLOWED_SESSION_TRANSITIONS: dict[UploadSessionStatus, tuple[UploadSessionStatus, ...]] = {
    UploadSessionStatus.UPLOADED: (UploadSessionStatus.PROCESSING,),
    UploadSessionStatus.PROCESSING: (
        UploadSessionStatus.COMPLETED,
        UploadSessionStatus.FAILED,
        UploadSessionStatus.DEGRADED,
    ),
    UploadSessionStatus.DEGRADED: (
        UploadSessionStatus.PROCESSING,
        UploadSessionStatus.COMPLETED,
        UploadSessionStatus.FAILED,
    ),
    UploadSessionStatus.COMPLETED: (),
    UploadSessionStatus.FAILED: (),
}


class UploadSession(TimestampMixin, Base):
    """教师答题卡上传批次（已上传→处理中→完成/失败，含降级分支）。"""

    __tablename__ = "upload_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    teacher_id: Mapped[int] = mapped_column(
        ForeignKey("teachers.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    title: Mapped[str | None] = mapped_column(String(128))
    total_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    status: Mapped[UploadSessionStatus] = mapped_column(
        sqlite_enum(UploadSessionStatus, name="upload_session_status"),
        default=UploadSessionStatus.UPLOADED,
        server_default=UploadSessionStatus.UPLOADED.value,
        nullable=False,
    )
    error_message: Mapped[str | None] = mapped_column(Text)
    uploaded_at: Mapped[datetime | None] = mapped_column(DateTime)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)

    def can_transition_to(self, new_status: UploadSessionStatus) -> bool:
        return new_status in ALLOWED_SESSION_TRANSITIONS[self.status]

    def transition_to(self, new_status: UploadSessionStatus) -> None:
        """应用层状态转移；非法回退抛 ValueError。"""
        if not self.can_transition_to(new_status):
            raise ValueError(
                f"非法会话状态转移: {self.status.value} -> {new_status.value}"
            )
        self.status = new_status


class OCRTask(TimestampMixin, Base):
    """单次批改任务（待处理→处理中→完成/失败）。"""

    __tablename__ = "ocr_tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("upload_sessions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    student_submission_id: Mapped[int | None] = mapped_column(
        ForeignKey("student_submissions.id", ondelete="SET NULL"), index=True
    )
    page_no: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[OCRTaskStatus] = mapped_column(
        sqlite_enum(OCRTaskStatus, name="ocr_task_status"),
        default=OCRTaskStatus.PENDING,
        server_default=OCRTaskStatus.PENDING.value,
        nullable=False,
    )
    ocr_result: Mapped[dict | None] = mapped_column(JSON)
    grading_result: Mapped[dict | None] = mapped_column(JSON)
    error_message: Mapped[str | None] = mapped_column(Text)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime)


class StudentSubmission(TimestampMixin, Base):
    """学生提交：原始/批改图片、答案列表 JSON、总分。"""

    __tablename__ = "student_submissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    exam_record_id: Mapped[int | None] = mapped_column(
        ForeignKey("exam_records.id", ondelete="SET NULL"), index=True
    )
    upload_session_id: Mapped[int | None] = mapped_column(
        ForeignKey("upload_sessions.id", ondelete="SET NULL"), index=True
    )
    original_image: Mapped[str | None] = mapped_column(String(512))
    graded_image: Mapped[str | None] = mapped_column(String(512))
    answers: Mapped[list | None] = mapped_column(JSON)
    total_score: Mapped[float | None] = mapped_column(Float)
    graded_at: Mapped[datetime | None] = mapped_column(DateTime)
