"""身份模型：Parent（家长）与 Account（统一账户，1:1 三选一）。"""
from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    String,
    event,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base
from backend.app.models.mixins import TimestampMixin


class Parent(TimestampMixin, Base):
    __tablename__ = "parents"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    phone: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String(128))
    password_hash: Mapped[str | None] = mapped_column(String(255))


class Account(TimestampMixin, Base):
    """统一账户：恰好关联 teacher / student / parent 之一（DB CHECK + 应用层双保险）。"""

    __tablename__ = "accounts"
    __table_args__ = (
        CheckConstraint(
            "(teacher_id IS NOT NULL) + (student_id IS NOT NULL) "
            "+ (parent_id IS NOT NULL) = 1",
            name="single_subject_fk",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    # 角色冗余快照（与所关联主体一致），便于中间件直接鉴权
    role: Mapped[str] = mapped_column(String(32), nullable=False)

    teacher_id: Mapped[int | None] = mapped_column(
        ForeignKey("teachers.id", ondelete="RESTRICT"), unique=True, index=True
    )
    student_id: Mapped[int | None] = mapped_column(
        ForeignKey("students.id", ondelete="RESTRICT"), unique=True, index=True
    )
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("parents.id", ondelete="RESTRICT"), unique=True, index=True
    )


def _validate_single_subject(_mapper, _connection, target: "Account") -> None:
    """应用层双保险：刷新前校验恰好关联一个主体（DB CHECK 是最后防线）。"""
    linked = sum(
        fk is not None
        for fk in (target.teacher_id, target.student_id, target.parent_id)
    )
    if linked != 1:
        raise ValueError(
            f"Account 必须恰好关联 teacher/student/parent 之一，当前关联数={linked}"
        )


event.listen(Account, "before_insert", _validate_single_subject)
event.listen(Account, "before_update", _validate_single_subject)
