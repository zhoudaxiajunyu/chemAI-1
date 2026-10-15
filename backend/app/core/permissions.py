"""RBAC：ROLE_PERMISSIONS 矩阵（22 号文档 §2.1 权威录入）+ 权限检查器。

矩阵粒度为 角色×资源×操作；"(自身)/(子女)" 的行级数据范围过滤不在本层，
由后续业务阶段在查询层实现。
"""
from dataclasses import dataclass
from typing import Callable

from fastapi import Depends, Request

# ---------- 资源与操作 ----------

RESOURCES = (
    "school", "grade", "class", "teacher", "student", "analysis",
    "exam", "question", "ocr", "grading", "diagnosis", "practice",
    "report", "panel", "parent", "notification", "warning",
)

ADMIN = "admin"
ACADEMIC_ADMIN = "academic_admin"
SUBJECT_LEADER = "subject_leader"
TEACHER = "teacher"
STUDENT = "student"
PARENT = "parent"

ROLES = (ADMIN, ACADEMIC_ADMIN, SUBJECT_LEADER, TEACHER, STUDENT, PARENT)

_R = frozenset({"read"})
_RW = frozenset({"read", "create"})


def _full_admin() -> dict[str, frozenset[str]]:
    actions = ("create", "read", "update", "delete", "bind", "send", "write")
    return {resource: frozenset(actions) for resource in RESOURCES}


# ---------- 22 号 §2.1 完整矩阵（逐格录入） ----------

ROLE_PERMISSIONS: dict[str, dict[str, frozenset[str]]] = {
    ADMIN: _full_admin(),

    ACADEMIC_ADMIN: {
        "school": frozenset({"read"}),
        "grade": frozenset({"create", "read", "update"}),
        "class": frozenset({"create", "read", "update", "delete"}),
        "teacher": frozenset({"read", "update"}),
        "student": frozenset({"create", "read", "update", "delete"}),
        "analysis": _R,
        "exam": _R, "question": _R, "ocr": _R, "grading": _R,
        "diagnosis": _R, "practice": _R, "report": _R, "panel": _R,
        "notification": _R, "warning": _R,
    },

    SUBJECT_LEADER: {
        # 所有资源仅 read，无任何写操作（parent 资源不开放）
        resource: _R
        for resource in (
            "school", "grade", "class", "teacher", "student", "analysis",
            "exam", "question", "ocr", "grading", "diagnosis", "practice",
            "report", "panel", "notification", "warning",
        )
    },

    TEACHER: {
        "school": _R, "grade": _R, "class": _R, "teacher": _R, "student": _R,
        "analysis": _R,
        "exam": _RW, "question": _RW, "ocr": _RW, "grading": _RW,
        "diagnosis": frozenset({"read", "update"}),
        "practice": _RW,
        "report": frozenset({"read", "send"}),
        "panel": _RW,
        # parent 资源仅学生与家长本人开放（22 号 §2.1 该列教师为 ❌）
        "notification": frozenset({"read", "write"}),
        "warning": frozenset({"read", "write"}),
    },

    STUDENT: {
        "grade": _R,
        "diagnosis": _R,
        "practice": _RW,
        "report": _R,
        "parent": frozenset({"read", "bind"}),
        "notification": frozenset({"read", "write"}),
        "warning": _R,
    },

    PARENT: {
        "student": _R,
        "analysis": _R,
        "report": _R,
        "parent": frozenset({"read", "bind"}),
        "notification": frozenset({"read", "write"}),
        "warning": _R,
    },
}


class PermissionDenied(Exception):
    """身份合法但权限不足（HTTP 403）。"""


@dataclass(frozen=True)
class UserContext:
    user_id: int
    role: str
    school_id: int | None = None


def has_permission(role: str, resource: str, action: str) -> bool:
    """矩阵查询：未声明的（角色，资源，操作）一律拒绝。"""
    perms = ROLE_PERMISSIONS.get(role)
    if perms is None:
        return False
    return action in perms.get(resource, frozenset())


def authorize(user: UserContext, resource: str, action: str) -> UserContext:
    """资源级校验；通过返回用户上下文，失败抛 PermissionDenied。"""
    if not has_permission(user.role, resource, action):
        raise PermissionDenied(
            f"角色 {user.role} 无权执行 {resource}:{action}"
        )
    return user


def require_permission(resource: str, action: str) -> Callable:
    """FastAPI 依赖（22 号文档所称"权限装饰器"的依赖注入形态）。

    与认证中间件配合：中间件校验 JWT 后把 UserContext 放在 request.state.user。
    """
    def _dependency(request: Request) -> UserContext:
        user: UserContext | None = getattr(request.state, "user", None)
        if user is None:  # 理论上中间件已拦截，防御性兜底
            raise PermissionDenied("缺少认证上下文")
        return authorize(user, resource, action)

    return _dependency


# 语义别名，便于端点同时声明依赖与阅读
def permit(resource: str, action: str):
    return Depends(require_permission(resource, action))
