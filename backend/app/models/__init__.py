"""模型包：导入即注册到 Base.metadata（Alembic 与测试 create_all 的单一来源）。"""
from backend.app.models.base import Base
from backend.app.models.enums import (
    ApprovalStatus,
    AuditStatus,
    BarrierType,
    BindingStatus,
    Difficulty,
    ExamType,
    GuardianRelation,
    NotificationType,
    OCRTaskStatus,
    QuestionSource,
    ReviewTaskStatus,
    TeacherRole,
    UploadSessionStatus,
    WarningLevel,
    WarningType,
)
from backend.app.models.organization import (
    Class,
    Grade,
    School,
    Student,
    Teacher,
    TeacherClassSubject,
)
from backend.app.models.identity import Account, Parent
from backend.app.models.teaching import ExamRecord, Question, StudentAnswer
from backend.app.models.diagnosis import (
    BarrierConfig,
    KnowledgePoint,
    ReviewTask,
    WarningLog,
)
from backend.app.models.family import ParentNotification, StudentParentBinding
from backend.app.models.ocr import OCRTask, StudentSubmission, UploadSession
from backend.app.models.bank import (
    HistoricalExam,
    HistoricalQuestion,
    QuestionSet,
    QuestionSetItem,
)

__all__ = [
    "Base",
    # enums
    "ApprovalStatus", "AuditStatus", "BarrierType", "BindingStatus", "Difficulty",
    "ExamType", "GuardianRelation", "NotificationType", "OCRTaskStatus",
    "QuestionSource", "ReviewTaskStatus", "TeacherRole", "UploadSessionStatus",
    "WarningLevel", "WarningType",
    # models
    "School", "Grade", "Class", "Teacher", "TeacherClassSubject", "Student",
    "Parent", "Account",
    "ExamRecord", "Question", "StudentAnswer",
    "BarrierConfig", "KnowledgePoint", "ReviewTask", "WarningLog",
    "StudentParentBinding", "ParentNotification",
    "UploadSession", "OCRTask", "StudentSubmission",
    "QuestionSet", "QuestionSetItem", "HistoricalExam", "HistoricalQuestion",
]
