"""全部枚举类型（str 混入，可直接 JSON 序列化）。

DB 层：sqlalchemy.Enum(native_enum=False, create_constraint=True) 落为 VARCHAR + CHECK。
应用层：赋非法值直接 ValueError；裸 SQL 绕过由 CHECK 兜底（双层保护）。
"""
import enum


# ---------- 组织 / 身份 ----------

class TeacherRole(str, enum.Enum):
    """教师体系 4 子角色（英文 code 入库，中文仅显示层映射）。"""

    ADMIN = "admin"                      # 系统管理员
    ACADEMIC_ADMIN = "academic_admin"    # 教务管理员
    SUBJECT_LEADER = "subject_leader"    # 学科组长
    TEACHER = "teacher"                  # 普通教师


# 角色中文显示名映射（禁止入库）
ROLE_DISPLAY_NAMES = {
    TeacherRole.ADMIN: "系统管理员",
    TeacherRole.ACADEMIC_ADMIN: "教务管理员",
    TeacherRole.SUBJECT_LEADER: "学科组长",
    TeacherRole.TEACHER: "普通教师",
}


class ApprovalStatus(str, enum.Enum):
    """教师/学生审核状态。教师默认 pending，学生默认 approved。"""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


# 兼容 tasks/设计中的别名
TeacherStatus = ApprovalStatus
StudentStatus = ApprovalStatus


# ---------- 教学链 ----------

class ExamType(str, enum.Enum):
    MONTHLY = "monthly"      # 月考（影响学情报告）
    PRACTICE = "practice"    # 练习（影响 ZPD 计算）
    HOMEWORK = "homework"    # 作业


class QuestionSource(str, enum.Enum):
    AI = "ai"
    MANUAL = "manual"
    DAILY_PRACTICE = "daily_practice"
    OCR = "ocr"


class AuditStatus(str, enum.Enum):
    """题目四维安全审核综合判定。blocked 题目不可下发学生。"""

    PASSED = "passed"
    WARNING = "warning"
    BLOCKED = "blocked"


class Difficulty(str, enum.Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    COMPETITION = "competition"  # 竞赛级不自动分配，仅手动录入


class BarrierType(str, enum.Enum):
    """障碍类型根因分类（代码与 26 号文档一致）。"""

    CONCEPT = "concept"      # 概念理解型
    READING = "reading"      # 审题障碍型
    EXPRESSION = "expression"  # 表述障碍型


# ---------- 诊断与学习 ----------

class ReviewTaskStatus(str, enum.Enum):
    """间隔复习任务三状态。级别 0-5 用整数列表达，5 为不再安排。"""

    DUE = "due"                  # 待复习
    OVERDUE = "overdue"          # 超期
    MASTERED = "mastered"        # 已掌握


class WarningType(str, enum.Enum):
    INACTIVE_LOGIN = "inactive_login"  # 连续未登录
    SCORE_DROP = "score_drop"          # 成绩下滑
    HIGH_ERROR_RATE = "high_error_rate"  # 高错误率
    NEW_BARRIER = "new_barrier"        # 新障碍出现


class WarningLevel(str, enum.Enum):
    WARNING = "warning"    # 警告
    CRITICAL = "critical"  # 严重
    INFO = "info"          # 提示


# ---------- 家校 ----------

class BindingStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class GuardianRelation(str, enum.Enum):
    FATHER = "father"
    MOTHER = "mother"
    OTHER = "other"


class NotificationType(str, enum.Enum):
    REPORT = "report"                  # 学习报告
    WARNING = "warning"               # 预警提醒
    TEACHER_MESSAGE = "teacher_message"  # 教师消息


# ---------- OCR 批改 ----------

class UploadSessionStatus(str, enum.Enum):
    UPLOADED = "uploaded"        # 已上传
    PROCESSING = "processing"    # 处理中
    DEGRADED = "degraded"        # 降级处理中（OCR→视觉模型）
    COMPLETED = "completed"      # 处理完成
    FAILED = "failed"            # 处理失败


class OCRTaskStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
