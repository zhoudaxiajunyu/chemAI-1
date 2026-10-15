"""诊断与学习模型测试（tasks 4.1-4.4）。"""
import pytest
from sqlalchemy.exc import IntegrityError

from backend.app.models.diagnosis import (
    BarrierConfig,
    KnowledgePoint,
    ReviewTask,
    WarningLog,
)
from backend.app.models.enums import (
    ReviewTaskStatus,
    WarningLevel,
    WarningType,
)
from backend.app.models.organization import Class, Grade, School, Student, Teacher
from backend.app.models.teaching import Question


@pytest.fixture
def student_and_question(db_session):
    school = School(name="S")
    db_session.add(school)
    db_session.flush()
    teacher = Teacher(name="T", school_id=school.id)
    grade = Grade(name="高一", school_id=school.id)
    db_session.add_all([teacher, grade])
    db_session.flush()
    cls = Class(name="1班", grade_id=grade.id)
    db_session.add(cls)
    db_session.flush()
    student = Student(name="Stu", class_id=cls.id)
    question = Question(stem="Q", difficulty="easy")
    db_session.add_all([student, question])
    db_session.flush()
    return teacher, student, question


# ---------- 4.1 BarrierConfig ----------

def test_barrier_config_defaults(db_session, student_and_question):
    teacher, _, _ = student_and_question
    cfg = BarrierConfig(teacher_id=teacher.id)
    db_session.add(cfg)
    db_session.commit()
    reloaded = db_session.get(BarrierConfig, cfg.id)
    assert (reloaded.concept_threshold, reloaded.reading_threshold,
            reloaded.expression_threshold, reloaded.mastery_threshold) == (3, 2, 3, 3)
    assert reloaded.auto_sync is False


def test_barrier_config_unique_per_teacher(db_session, student_and_question):
    teacher, _, _ = student_and_question
    db_session.add(BarrierConfig(teacher_id=teacher.id))
    db_session.flush()
    db_session.add(BarrierConfig(teacher_id=teacher.id))
    with pytest.raises(IntegrityError):
        db_session.flush()


# ---------- 4.2 KnowledgePoint ----------

def test_knowledge_point_fields(db_session):
    kp = KnowledgePoint(
        name="氧化还原反应", category="基础概念", pubchem_id="RX-001",
        related_question_count=12, dynamic_error_rate=0.37,
    )
    db_session.add(kp)
    db_session.commit()
    reloaded = db_session.get(KnowledgePoint, kp.id)
    assert reloaded.name == "氧化还原反应"
    assert reloaded.related_question_count == 12
    assert reloaded.dynamic_error_rate == 0.37


# ---------- 4.3 ReviewTask ----------

def test_review_task_defaults_and_history_json(db_session, student_and_question):
    _, student, question = student_and_question
    task = ReviewTask(
        student_id=student.id, question_id=question.id,
        review_history=[{"date": "2026-10-15", "result": "wrong"}],
    )
    db_session.add(task)
    db_session.commit()
    reloaded = db_session.get(ReviewTask, task.id)
    assert reloaded.level == 0
    assert reloaded.status is ReviewTaskStatus.DUE
    assert isinstance(reloaded.review_history, list)
    assert reloaded.review_history[0]["result"] == "wrong"


def test_review_task_level_range_check(db_session, student_and_question):
    _, student, question = student_and_question
    db_session.add(ReviewTask(student_id=student.id, question_id=question.id, level=6))
    with pytest.raises(IntegrityError, match="level_range"):
        db_session.flush()


def test_review_task_status_enum(db_session, student_and_question):
    _, student, question = student_and_question
    task = ReviewTask(
        student_id=student.id, question_id=question.id, status=ReviewTaskStatus.MASTERED
    )
    db_session.add(task)
    db_session.commit()
    assert db_session.get(ReviewTask, task.id).status is ReviewTaskStatus.MASTERED


# ---------- 4.4 WarningLog ----------

def test_warning_log_fields(db_session, student_and_question):
    _, student, _ = student_and_question
    log = WarningLog(
        student_id=student.id,
        warning_type=WarningType.NEW_BARRIER,
        level=WarningLevel.CRITICAL,
        message="出现概念理解障碍",
        notified_teacher=True,
    )
    db_session.add(log)
    db_session.commit()
    reloaded = db_session.get(WarningLog, log.id)
    assert reloaded.warning_type is WarningType.NEW_BARRIER
    assert reloaded.level is WarningLevel.CRITICAL
    assert reloaded.notified_teacher is True
    assert reloaded.notified_parent is False
    assert reloaded.is_read is False
