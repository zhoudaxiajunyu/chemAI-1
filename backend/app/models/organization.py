"""核心组织模型：School / Grade / Class / Teacher / TeacherClassSubject / Student。

组织链：School -> Grade -> Class -> Student；教师归属学校，通过任课关系关联班级。
"""
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, sqlite_enum
from backend.app.models.enums import ApprovalStatus, TeacherRole
from backend.app.models.mixins import TimestampMixin


class School(TimestampMixin, Base):
    __tablename__ = "schools"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    region: Mapped[str | None] = mapped_column(String(128))
    address: Mapped[str | None] = mapped_column(String(256))
    phone: Mapped[str | None] = mapped_column(String(32))
    current_term: Mapped[str | None] = mapped_column(String(64))  # 当前学期

    grades: Mapped[list["Grade"]] = relationship(back_populates="school")


class Grade(TimestampMixin, Base):
    __tablename__ = "grades"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)  # 高一/高二/高三
    school_year: Mapped[str | None] = mapped_column(String(32))    # 所属学年
    school_id: Mapped[int] = mapped_column(
        ForeignKey("schools.id", ondelete="RESTRICT"), index=True, nullable=False
    )

    school: Mapped["School"] = relationship(back_populates="grades")
    classes: Mapped[list["Class"]] = relationship(back_populates="grade")


class Class(TimestampMixin, Base):
    __tablename__ = "classes"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    grade_id: Mapped[int] = mapped_column(
        ForeignKey("grades.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    head_teacher_id: Mapped[int | None] = mapped_column(
        ForeignKey("teachers.id", ondelete="SET NULL"), index=True
    )
    student_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    stage: Mapped[str | None] = mapped_column(String(16))   # 学段：high / junior
    subject: Mapped[str] = mapped_column(String(32), default="化学", server_default="化学")

    grade: Mapped["Grade"] = relationship(back_populates="classes")
    students: Mapped[list["Student"]] = relationship(back_populates="class_")


class Teacher(TimestampMixin, Base):
    __tablename__ = "teachers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(32), index=True)
    school_id: Mapped[int] = mapped_column(
        ForeignKey("schools.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    # 教师默认待审核
    status: Mapped[ApprovalStatus] = mapped_column(
        sqlite_enum(ApprovalStatus, name="teacher_status"),
        default=ApprovalStatus.PENDING, server_default=ApprovalStatus.PENDING.value,
        nullable=False,
    )
    role: Mapped[TeacherRole] = mapped_column(
        sqlite_enum(TeacherRole, name="teacher_role"),
        default=TeacherRole.TEACHER, server_default=TeacherRole.TEACHER.value,
        nullable=False,
    )


class TeacherClassSubject(TimestampMixin, Base):
    """教师-班级任课关系（多对多，标注班主任）。"""

    __tablename__ = "teacher_class_subjects"

    id: Mapped[int] = mapped_column(primary_key=True)
    teacher_id: Mapped[int] = mapped_column(
        ForeignKey("teachers.id", ondelete="CASCADE"), index=True, nullable=False
    )
    class_id: Mapped[int] = mapped_column(
        ForeignKey("classes.id", ondelete="CASCADE"), index=True, nullable=False
    )
    subject: Mapped[str] = mapped_column(
        String(32), default="化学", server_default="化学", nullable=False
    )
    is_headteacher: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="0"
    )


class Student(TimestampMixin, Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    class_id: Mapped[int] = mapped_column(
        ForeignKey("classes.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    student_number: Mapped[str | None] = mapped_column(String(64))
    # 学生默认免审
    status: Mapped[ApprovalStatus] = mapped_column(
        sqlite_enum(ApprovalStatus, name="student_status"),
        default=ApprovalStatus.APPROVED, server_default=ApprovalStatus.APPROVED.value,
        nullable=False,
    )
    # 障碍画像 JSON：{"concept": float, "reading": float, "expression": float}
    barrier_profile: Mapped[dict | None] = mapped_column(JSON)
    # 练习追踪
    practice_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    last_practice_at: Mapped[datetime | None] = mapped_column(DateTime)
    # 6 位家长绑定码
    bind_code: Mapped[str | None] = mapped_column(String(6), index=True)

    class_: Mapped["Class"] = relationship(back_populates="students")
