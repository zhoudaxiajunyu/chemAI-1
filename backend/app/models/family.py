"""家校模型：StudentParentBinding / ParentNotification。"""
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, sqlite_enum
from backend.app.models.enums import BindingStatus, GuardianRelation, NotificationType
from backend.app.models.mixins import TimestampMixin


class StudentParentBinding(TimestampMixin, Base):
    """亲子绑定：凭学生 6 位绑定码建立，可 active/inactive。"""

    __tablename__ = "student_parent_bindings"
    __table_args__ = (
        UniqueConstraint("student_id", "parent_id", name="student_parent"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), index=True, nullable=False
    )
    parent_id: Mapped[int] = mapped_column(
        ForeignKey("parents.id", ondelete="CASCADE"), index=True, nullable=False
    )
    bind_code: Mapped[str] = mapped_column(String(6), nullable=False)
    relation: Mapped[GuardianRelation | None] = mapped_column(
        sqlite_enum(GuardianRelation, name="guardian_relation")
    )
    status: Mapped[BindingStatus] = mapped_column(
        sqlite_enum(BindingStatus, name="binding_status"),
        default=BindingStatus.ACTIVE, server_default=BindingStatus.ACTIVE.value,
        nullable=False,
    )
    bound_at: Mapped[datetime | None] = mapped_column(DateTime)
    unbound_at: Mapped[datetime | None] = mapped_column(DateTime)


class ParentNotification(TimestampMixin, Base):
    """家长通知：学习报告/预警提醒/教师消息。"""

    __tablename__ = "parent_notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    parent_id: Mapped[int] = mapped_column(
        ForeignKey("parents.id", ondelete="CASCADE"), index=True, nullable=False
    )
    notification_type: Mapped[NotificationType] = mapped_column(
        sqlite_enum(NotificationType, name="notification_type"), nullable=False
    )
    title: Mapped[str | None] = mapped_column(String(128))
    content: Mapped[str | None] = mapped_column(Text)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, index=True)
