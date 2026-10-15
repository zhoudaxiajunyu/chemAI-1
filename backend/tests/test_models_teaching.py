"""考试与作答模型测试（tasks 3.1-3.3）。"""
import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from backend.app.models.enums import (
    AuditStatus,
    BarrierType,
    Difficulty,
    ExamType,
    QuestionSource,
)
from backend.app.models.organization import Class, Grade, School, Student, Teacher
from backend.app.models.teaching import ExamRecord, Question, StudentAnswer


@pytest.fixture
def chain(db_session):
    school = School(name="S")
    db_session.add(school)
    db_session.flush()
    grade = Grade(name="高一", school_id=school.id)
    db_session.add(grade)
    db_session.flush()
    cls = Class(name="1班", grade_id=grade.id)
    db_session.add(cls)
    db_session.flush()
    teacher = Teacher(name="T", school_id=school.id)
    db_session.add(teacher)
    student = Student(name="Stu", class_id=cls.id)
    db_session.add(student)
    db_session.flush()
    return school, cls, teacher, student


# ---------- 3.1 ExamRecord ----------

def test_exam_record_belongs_to_class(db_session, chain):
    _, cls, _, _ = chain
    exam = ExamRecord(title="第一次月考", class_id=cls.id, exam_type=ExamType.MONTHLY)
    db_session.add(exam)
    db_session.flush()
    assert exam.class_id == cls.id


def test_exam_type_db_check(db_session, chain):
    _, cls, _, _ = chain
    with pytest.raises(IntegrityError, match="exam_type"):
        db_session.execute(
            text("INSERT INTO exam_records (class_id, exam_type) VALUES (:cid, 'final')"),
            {"cid": cls.id},
        )


def test_exam_statistics_json(db_session, chain):
    _, cls, _, _ = chain
    stats = {
        "per_question": [{"question_no": 1, "error_rate": 0.42}],
        "knowledge_ranking": [{"kp": "氧化还原", "error_rate": 0.5}],
        "class_average": 78.5,
    }
    exam = ExamRecord(class_id=cls.id, exam_type=ExamType.MONTHLY, statistics=stats)
    db_session.add(exam)
    db_session.commit()
    reloaded = db_session.get(ExamRecord, exam.id)
    assert isinstance(reloaded.statistics, dict)
    assert reloaded.statistics["class_average"] == 78.5
    assert reloaded.statistics["per_question"][0]["error_rate"] == 0.42


# ---------- 3.2 Question ----------

def test_question_enums_and_audit_report_json(db_session):
    report = {
        "coefficient_balancing": {"status": "passed"},
        "reaction_conditions": {"status": "warning"},
        "products": {"status": "passed"},
        "molecular_structure": {"status": "passed"},
        "overall_status": "warning",
    }
    q = Question(
        stem="配平：H2 + O2 -> ?",
        options=["H2O", "HO2", "H2O2", "OH"],
        difficulty=Difficulty.MEDIUM,
        source=QuestionSource.AI,
        audit_status=AuditStatus.WARNING,
        audit_report=report,
    )
    db_session.add(q)
    db_session.commit()
    reloaded = db_session.get(Question, q.id)
    assert reloaded.difficulty is Difficulty.MEDIUM
    assert reloaded.source is QuestionSource.AI
    assert reloaded.audit_status is AuditStatus.WARNING
    assert isinstance(reloaded.audit_report, dict)
    assert reloaded.audit_report["overall_status"] == "warning"
    assert reloaded.options[0] == "H2O"


def test_question_difficulty_db_check(db_session):
    with pytest.raises(IntegrityError, match="question_difficulty"):
        db_session.execute(
            text("INSERT INTO questions (stem, difficulty) VALUES ('x', 'extreme')")
        )


def test_question_app_layer_invalid_difficulty():
    with pytest.raises(ValueError):
        Difficulty("extreme")


# ---------- 3.3 StudentAnswer ----------

def test_student_answer_triple_link(db_session, chain):
    _, cls, _, student = chain
    exam = ExamRecord(class_id=cls.id, exam_type=ExamType.HOMEWORK)
    q = Question(stem="1+1=?", difficulty=Difficulty.EASY)
    db_session.add_all([exam, q])
    db_session.flush()
    ans = StudentAnswer(
        student_id=student.id,
        question_id=q.id,
        exam_record_id=exam.id,
        is_correct=False,
        barrier_type=BarrierType.CONCEPT,
        consecutive_error_count=3,
    )
    db_session.add(ans)
    db_session.commit()
    reloaded = db_session.get(StudentAnswer, ans.id)
    assert (reloaded.student_id, reloaded.question_id, reloaded.exam_record_id) == (
        student.id, q.id, exam.id,
    )
    assert reloaded.barrier_type is BarrierType.CONCEPT
    assert reloaded.consecutive_error_count == 3


def test_student_answer_fk_enforced(db_session):
    with pytest.raises(IntegrityError):
        db_session.add(StudentAnswer(student_id=999999, question_id=999999))
        db_session.flush()
