"""核心组织与身份模型测试（tasks 2.1-2.6）。"""
import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from backend.app.models.identity import Account, Parent
from backend.app.models.organization import (
    Class,
    Grade,
    School,
    Student,
    Teacher,
    TeacherClassSubject,
)
from backend.app.models.enums import ApprovalStatus, TeacherRole


# ---------- fixtures ----------

@pytest.fixture
def school(db_session):
    s = School(name="第一中学", region="湖南")
    db_session.add(s)
    db_session.flush()
    return s


@pytest.fixture
def grade(db_session, school):
    g = Grade(name="高一", school_year="2026", school_id=school.id)
    db_session.add(g)
    db_session.flush()
    return g


@pytest.fixture
def class_(db_session, grade):
    c = Class(name="高一(3)班", grade_id=grade.id, stage="high")
    db_session.add(c)
    db_session.flush()
    return c


@pytest.fixture
def teacher(db_session, school):
    t = Teacher(name="王老师", phone="13800000001", school_id=school.id)
    db_session.add(t)
    db_session.flush()
    return t


@pytest.fixture
def student(db_session, class_):
    s = Student(name="李同学", class_id=class_.id)
    db_session.add(s)
    db_session.flush()
    return s


@pytest.fixture
def parent(db_session):
    p = Parent(name="李父", phone="13900000001", password_hash="x")
    db_session.add(p)
    db_session.flush()
    return p


# ---------- 2.1 组织链 ----------

def test_org_chain_create_and_trace(db_session, school, grade, class_, student):
    # 沿外键链可回溯到学校
    g = db_session.get(Grade, grade.id)
    assert g.school_id == school.id
    c = db_session.get(Class, class_.id)
    assert c.grade_id == grade.id
    s = db_session.get(Student, student.id)
    assert s.class_id == class_.id
    assert s.class_.grade.school.id == school.id


def test_orphan_grade_rejected(db_session):
    db_session.add(Grade(name="高九", school_id=999999))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_delete_school_with_children_rejected(db_session, school, grade):
    db_session.delete(school)
    with pytest.raises(IntegrityError):
        db_session.flush()


# ---------- 2.2 Teacher ----------

def test_teacher_defaults_pending(db_session, teacher):
    assert teacher.status is ApprovalStatus.PENDING
    assert teacher.role is TeacherRole.TEACHER


def test_teacher_role_app_layer_invalid():
    # 应用层边界：请求数据转枚举成员时即拒绝（Pydantic/schema 走同一构造）
    with pytest.raises(ValueError):
        TeacherRole("superadmin")


def test_teacher_role_db_check_invalid(db_session, school):
    # 裸 SQL 绕过应用层时，DB CHECK 在执行点兜底
    with pytest.raises(IntegrityError, match="teacher_role"):
        db_session.execute(
            text("INSERT INTO teachers (name, school_id, role) VALUES ('裸SQL', :sid, 'superadmin')"),
            {"sid": school.id},
        )


# ---------- 2.3 Student ----------

def test_student_defaults_approved(db_session, student):
    assert student.status is ApprovalStatus.APPROVED


def test_student_barrier_profile_json(db_session, student):
    student.barrier_profile = {"concept": 0.3, "reading": 0.5, "expression": 0.2}
    db_session.commit()

    reloaded = db_session.get(Student, student.id)
    assert isinstance(reloaded.barrier_profile, dict)
    assert reloaded.barrier_profile["reading"] == 0.5


def test_student_bind_code(db_session, student):
    student.bind_code = "123456"
    db_session.commit()
    assert db_session.get(Student, student.id).bind_code == "123456"


# ---------- 2.4 Account 三选一 ----------

def test_account_teacher_ok(db_session, teacher):
    acc = Account(username="t1", password_hash="h", role="teacher", teacher_id=teacher.id)
    db_session.add(acc)
    db_session.commit()
    assert db_session.get(Account, acc.id).teacher_id == teacher.id


def test_account_student_ok(db_session, student):
    acc = Account(username="s1", password_hash="h", role="student", student_id=student.id)
    db_session.add(acc)
    db_session.commit()
    assert db_session.get(Account, acc.id).student_id == student.id


def test_account_parent_ok(db_session, parent):
    acc = Account(username="p1", password_hash="h", role="parent", parent_id=parent.id)
    db_session.add(acc)
    db_session.commit()
    assert db_session.get(Account, acc.id).parent_id == parent.id


def test_account_double_fk_rejected_at_app_layer(db_session, teacher, student):
    # 应用层双保险：before_insert 事件先于 DB CHECK 抛 ValueError
    acc = Account(username="both", password_hash="h", role="teacher",
                  teacher_id=teacher.id, student_id=student.id)
    db_session.add(acc)
    with pytest.raises(ValueError, match="恰好关联"):
        db_session.flush()


def test_account_no_fk_rejected_at_app_layer(db_session):
    acc = Account(username="none", password_hash="h", role="teacher")
    db_session.add(acc)
    with pytest.raises(ValueError, match="恰好关联"):
        db_session.flush()


def test_account_check_constraint_is_db_backstop(db_session):
    # 裸 SQL 绕过 ORM 事件时，single_subject_fk CHECK 兜底
    with pytest.raises(IntegrityError, match="single_subject_fk"):
        db_session.execute(text(
            "INSERT INTO accounts (username, password_hash, role) "
            "VALUES ('raw_none', 'h', 'teacher')"
        ))


def test_account_username_unique(db_session, teacher):
    db_session.add(Account(username="dup", password_hash="h", role="teacher",
                           teacher_id=teacher.id))
    db_session.commit()
    other_teacher = Teacher(name="另一个", school_id=teacher.school_id)
    db_session.add(other_teacher)
    db_session.flush()
    db_session.add(Account(username="dup", password_hash="h2", role="teacher",
                           teacher_id=other_teacher.id))
    with pytest.raises(IntegrityError):
        db_session.flush()


# ---------- 2.5 TeacherClassSubject ----------

def test_teacher_multiple_classes_headteacher(db_session, teacher, class_):
    other_grade = Grade(name="高二", school_id=class_.grade.school_id)
    db_session.add(other_grade)
    db_session.flush()
    other_class = Class(name="高二(1)班", grade_id=other_grade.id, stage="high")
    db_session.add(other_class)
    db_session.flush()

    db_session.add_all([
        TeacherClassSubject(teacher_id=teacher.id, class_id=class_.id, is_headteacher=True),
        TeacherClassSubject(teacher_id=teacher.id, class_id=other_class.id),
    ])
    db_session.commit()

    links = db_session.query(TeacherClassSubject).filter_by(teacher_id=teacher.id).all()
    assert len(links) == 2
    head = [x for x in links if x.is_headteacher]
    assert len(head) == 1 and head[0].class_id == class_.id


def test_teaching_link_fk_enforced(db_session):
    db_session.add(TeacherClassSubject(teacher_id=999999, class_id=999999))
    with pytest.raises(IntegrityError):
        db_session.flush()
