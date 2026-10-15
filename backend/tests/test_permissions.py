"""RBAC 矩阵与权限检查器测试（tasks 9.1-9.2）。"""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.core.jwt import create_access_token
from backend.app.core.permissions import (
    PARENT,
    RESOURCES,
    ROLES,
    ROLE_PERMISSIONS,
    STUDENT,
    SUBJECT_LEADER,
    TEACHER,
    ACADEMIC_ADMIN,
    ADMIN,
    PermissionDenied,
    UserContext,
    authorize,
    has_permission,
    permit,
    require_permission,
)

ALL_ACTIONS = ("create", "read", "update", "delete", "bind", "send", "write")


# ---------- 9.1 矩阵结构完备性 ----------

def test_matrix_has_six_roles_and_seventeen_resources():
    assert set(ROLES) == {
        ADMIN, ACADEMIC_ADMIN, SUBJECT_LEADER, TEACHER, STUDENT, PARENT
    }
    assert len(RESOURCES) == 17
    for role, perms in ROLE_PERMISSIONS.items():
        assert set(perms).issubset(set(RESOURCES)), role
        for actions in perms.values():
            assert set(actions).issubset(set(ALL_ACTIONS)), role


@pytest.mark.parametrize("resource", RESOURCES)
@pytest.mark.parametrize("action", ALL_ACTIONS)
def test_admin_allows_everything(resource, action):
    assert has_permission(ADMIN, resource, action) is True


@pytest.mark.parametrize("role", [r for r in ROLES if r != ADMIN])
@pytest.mark.parametrize("bogus", ["execute", "drop", "export_all", "impersonate"])
def test_undeclared_action_denied(role, bogus):
    assert has_permission(role, "school", bogus) is False


def test_unknown_role_resource_denied():
    assert has_permission("ghost", "school", "read") is False
    assert has_permission(TEACHER, "nuclear_codes", "read") is False


# ---------- specs/authorization 逐场景关键断言 ----------

@pytest.mark.parametrize("case", [
    # 教务管理员
    (ACADEMIC_ADMIN, "class", "create", True),
    (ACADEMIC_ADMIN, "school", "delete", False),
    (ACADEMIC_ADMIN, "student", "delete", True),
    (ACADEMIC_ADMIN, "exam", "create", False),
    # 学科组长只读
    (SUBJECT_LEADER, "exam", "read", True),
    (SUBJECT_LEADER, "exam", "create", False),
    (SUBJECT_LEADER, "school", "read", True),
    (SUBJECT_LEADER, "notification", "write", False),
    # 教师教学写
    (TEACHER, "question", "create", True),
    (TEACHER, "school", "update", False),
    (TEACHER, "report", "send", True),
    (TEACHER, "warning", "write", True),
    # 22 号 §2.1：parent 资源对教师不开放（学生与家长本人才有）
    (TEACHER, "parent", "read", False),
    (TEACHER, "parent", "bind", False),
    (STUDENT, "parent", "read", True),
    # 学生自身数据
    (STUDENT, "practice", "create", True),
    (STUDENT, "question", "read", False),
    (STUDENT, "diagnosis", "read", True),
    (STUDENT, "parent", "bind", True),
    # 家长最小可见
    (PARENT, "report", "read", True),
    (PARENT, "panel", "read", False),
    (PARENT, "student", "read", True),
    (PARENT, "exam", "read", False),
])
def test_matrix_key_cells(case):
    role, resource, action, expected = case
    assert has_permission(role, resource, action) is expected


# ---------- 9.2 authorize / require_permission ----------

def test_authorize_returns_context():
    user = UserContext(user_id=7, role=TEACHER, school_id=3)
    result = authorize(user, "exam", "create")
    assert result is user


def test_authorize_denies():
    user = UserContext(user_id=8, role=STUDENT)
    with pytest.raises(PermissionDenied):
        authorize(user, "exam", "create")


def test_require_permission_dependency_via_http():
    from fastapi.responses import JSONResponse
    from backend.app.core.middleware import AuthMiddleware

    app = FastAPI()
    app.add_middleware(AuthMiddleware)

    @app.exception_handler(PermissionDenied)
    def _denied(_, exc):
        return JSONResponse(status_code=403, content={"detail": str(exc)})

    @app.get("/api/classes")
    def _route(user=permit("class", "read")):
        return {"user_id": user.user_id, "role": user.role}

    client = TestClient(app)

    teacher_token = create_access_token(7, TEACHER, school_id=1)
    student_token = create_access_token(8, STUDENT)

    r_ok = client.get("/api/classes", headers={"Authorization": f"Bearer {teacher_token}"})
    assert r_ok.status_code == 200
    assert r_ok.json() == {"user_id": 7, "role": TEACHER}

    r_deny = client.get("/api/classes", headers={"Authorization": f"Bearer {student_token}"})
    assert r_deny.status_code == 403
