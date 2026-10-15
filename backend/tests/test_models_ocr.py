"""OCR 批改模型测试（tasks 6.1-6.3）。"""
import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from backend.app.models.enums import OCRTaskStatus, UploadSessionStatus
from backend.app.models.ocr import OCRTask, StudentSubmission, UploadSession
from backend.app.models.organization import (
    Class,
    Grade,
    School,
    Student,
    Teacher,
)
from backend.app.models.teaching import ExamRecord


@pytest.fixture
def ocr_chain(db_session):
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
    exam = ExamRecord(class_id=cls.id, exam_type="monthly")
    db_session.add_all([student, exam])
    db_session.flush()
    return teacher, student, exam


# ---------- 6.1 UploadSession ----------

def test_upload_session_default_status(db_session, ocr_chain):
    teacher, _, _ = ocr_chain
    session = UploadSession(teacher_id=teacher.id, title="10 月月考批次")
    db_session.add(session)
    db_session.commit()
    assert db_session.get(UploadSession, session.id).status is UploadSessionStatus.UPLOADED


def test_upload_session_valid_transitions(db_session, ocr_chain):
    teacher, _, _ = ocr_chain
    session = UploadSession(teacher_id=teacher.id)
    db_session.add(session)
    db_session.flush()
    session.transition_to(UploadSessionStatus.PROCESSING)
    assert session.status is UploadSessionStatus.PROCESSING
    session.transition_to(UploadSessionStatus.DEGRADED)
    session.transition_to(UploadSessionStatus.PROCESSING)
    session.transition_to(UploadSessionStatus.COMPLETED)
    assert session.status is UploadSessionStatus.COMPLETED


def test_upload_session_illegal_reversal_rejected(db_session, ocr_chain):
    teacher, _, _ = ocr_chain
    session = UploadSession(teacher_id=teacher.id, status=UploadSessionStatus.COMPLETED)
    db_session.add(session)
    db_session.flush()
    with pytest.raises(ValueError, match="非法会话状态转移"):
        session.transition_to(UploadSessionStatus.PROCESSING)


def test_upload_session_status_db_check(db_session, ocr_chain):
    teacher, _, _ = ocr_chain
    with pytest.raises(IntegrityError, match="upload_session_status"):
        db_session.execute(
            text("INSERT INTO upload_sessions (teacher_id, status) "
                 "VALUES (:tid, 'archived')"),
            {"tid": teacher.id},
        )


# ---------- 6.2 OCRTask ----------

def test_ocr_task_fields_and_fk(db_session, ocr_chain):
    teacher, _, _ = ocr_chain
    session = UploadSession(teacher_id=teacher.id)
    db_session.add(session)
    db_session.flush()
    task = OCRTask(
        session_id=session.id, page_no=1,
        status=OCRTaskStatus.COMPLETED,
        ocr_result={"raw": "Fe + CuSO4 -> FeSO4 + Cu"},
        grading_result={"score": 8.5},
    )
    db_session.add(task)
    db_session.commit()
    reloaded = db_session.get(OCRTask, task.id)
    assert reloaded.session_id == session.id
    assert reloaded.status is OCRTaskStatus.COMPLETED
    assert reloaded.ocr_result["raw"].startswith("Fe")
    assert reloaded.grading_result["score"] == 8.5


def test_ocr_task_session_fk_enforced(db_session):
    db_session.add(OCRTask(session_id=999999))
    with pytest.raises(IntegrityError):
        db_session.flush()


# ---------- 6.3 StudentSubmission ----------

def test_student_submission(db_session, ocr_chain):
    teacher, student, exam = ocr_chain
    answers = [
        {"question_no": 1, "answer": "H2O", "is_correct": True, "score": 2.0},
        {"question_no": 2, "answer": "HO2", "is_correct": False, "score": 0.0},
    ]
    sub = StudentSubmission(
        student_id=student.id, exam_record_id=exam.id,
        original_image="data/uploads/raw/1.png",
        graded_image="data/uploads/graded/1.png",
        answers=answers, total_score=2.0,
    )
    db_session.add(sub)
    db_session.commit()
    reloaded = db_session.get(StudentSubmission, sub.id)
    assert reloaded.student_id == student.id
    assert reloaded.exam_record_id == exam.id
    assert isinstance(reloaded.answers, list)
    assert reloaded.answers[1]["answer"] == "HO2"
    assert reloaded.total_score == 2.0
