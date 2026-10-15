"""题库模型测试（tasks 7.1-7.3）。"""
import pytest
from sqlalchemy.exc import IntegrityError

from backend.app.models.bank import (
    HistoricalExam,
    HistoricalQuestion,
    QuestionSet,
    QuestionSetItem,
)
from backend.app.models.teaching import Question


@pytest.fixture
def two_sets(db_session):
    s1 = QuestionSet(name="2025 长沙真题", source_region="长沙", year=2025)
    s2 = QuestionSet(name="2024 湖南真题", source_region="湖南", year=2024)
    db_session.add_all([s1, s2])
    db_session.flush()
    return s1, s2


# ---------- 7.1 QuestionSet ----------

def test_question_set_fields(db_session, two_sets):
    s1, _ = two_sets
    assert s1.name == "2025 长沙真题"
    assert s1.year == 2025


# ---------- 7.2 QuestionSetItem ----------

def test_one_question_in_multiple_sets(db_session, two_sets):
    s1, s2 = two_sets
    q = Question(stem="配平题", difficulty="easy")
    db_session.add(q)
    db_session.flush()
    db_session.add_all([
        QuestionSetItem(set_id=s1.id, question_id=q.id, sort_order=1),
        QuestionSetItem(set_id=s2.id, question_id=q.id, sort_order=3),
    ])
    db_session.commit()
    items = db_session.query(QuestionSetItem).filter_by(question_id=q.id).all()
    by_set = {item.set_id: item.sort_order for item in items}
    assert by_set == {s1.id: 1, s2.id: 3}


def test_question_set_item_unique_pair(db_session, two_sets):
    s1, _ = two_sets
    q = Question(stem="Q", difficulty="easy")
    db_session.add(q)
    db_session.flush()
    db_session.add_all([
        QuestionSetItem(set_id=s1.id, question_id=q.id, sort_order=1),
        QuestionSetItem(set_id=s1.id, question_id=q.id, sort_order=2),
    ])
    with pytest.raises(IntegrityError):
        db_session.flush()


# ---------- 7.3 HistoricalExam / HistoricalQuestion ----------

def test_historical_exam_and_question(db_session):
    exam = HistoricalExam(title="2025 高考湖南卷", source="高考", region="湖南", year=2025)
    db_session.add(exam)
    db_session.flush()
    hq = HistoricalQuestion(
        exam_id=exam.id, question_no="26(1)",
        knowledge_point_ids=["氧化还原", "电子守恒"],
        difficulty=0.42, discrimination=0.58,
        stem="工业上用...写出反应方程式",
        answer="2Fe3+ + Cu -> 2Fe2+ + Cu2+",
        explanation="考查电子守恒配平",
    )
    db_session.add(hq)
    db_session.commit()
    reloaded = db_session.get(HistoricalQuestion, hq.id)
    assert reloaded.exam_id == exam.id
    assert reloaded.knowledge_point_ids[1] == "电子守恒"
    assert reloaded.difficulty == 0.42
    assert reloaded.discrimination == 0.58
    assert reloaded.answer.startswith("2Fe3+")
