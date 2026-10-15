"""家校绑定与通知模型测试（tasks 5.1-5.2）。"""
from datetime import datetime

import pytest
from sqlalchemy.exc import IntegrityError

from backend.app.models.enums import (
    BindingStatus,
    GuardianRelation,
    NotificationType,
)
from backend.app.models.family import ParentNotification, StudentParentBinding
from backend.app.models.identity import Parent
from backend.app.models.organization import Class, Grade, School, Student


def _make_student_parent(db_session, bind_code="123456"):
    school = School(name="S")
    db_session.add(school)
    db_session.flush()
    grade = Grade(name="高一", school_id=school.id)
    db_session.add(grade)
    db_session.flush()
    cls = Class(name="1班", grade_id=grade.id)
    db_session.add(cls)
    db_session.flush()
    student = Student(name="Stu", class_id=cls.id, bind_code=bind_code)
    parent = Parent(name="P", phone=f"139{bind_code}", password_hash="h")
    db_session.add_all([student, parent])
    db_session.flush()
    return student, parent


# ---------- 5.1 StudentParentBinding ----------

def test_binding_via_bind_code(db_session):
    student, parent = _make_student_parent(db_session, "246810")
    binding = StudentParentBinding(
        student_id=student.id, parent_id=parent.id,
        bind_code=student.bind_code, relation=GuardianRelation.FATHER,
    )
    db_session.add(binding)
    db_session.commit()
    reloaded = db_session.get(StudentParentBinding, binding.id)
    assert reloaded.status is BindingStatus.ACTIVE
    assert reloaded.relation is GuardianRelation.FATHER
    assert reloaded.bind_code == "246810"


def test_binding_duplicate_rejected(db_session):
    student, parent = _make_student_parent(db_session)
    db_session.add(StudentParentBinding(
        student_id=student.id, parent_id=parent.id, bind_code="123456"))
    db_session.flush()
    db_session.add(StudentParentBinding(
        student_id=student.id, parent_id=parent.id, bind_code="123456"))
    with pytest.raises(IntegrityError):
        db_session.flush()


# ---------- 5.2 ParentNotification ----------

def test_parent_notification_defaults(db_session):
    student, parent = _make_student_parent(db_session)
    note = ParentNotification(
        parent_id=parent.id,
        notification_type=NotificationType.REPORT,
        title="10 月学情报告",
        sent_at=datetime(2026, 10, 15),
    )
    db_session.add(note)
    db_session.commit()
    reloaded = db_session.get(ParentNotification, note.id)
    assert reloaded.notification_type is NotificationType.REPORT
    assert reloaded.is_read is False
    assert reloaded.sent_at.year == 2026
