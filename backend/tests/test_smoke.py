"""冒烟测试：验证测试基建可被发现、枚举可导入。"""
from backend.app.models.enums import (
    BarrierType,
    ExamType,
    TeacherRole,
)


def test_enum_values():
    assert ExamType.MONTHLY.value == "monthly"
    assert BarrierType.CONCEPT.value == "concept"
    assert TeacherRole.ACADEMIC_ADMIN.value == "academic_admin"
