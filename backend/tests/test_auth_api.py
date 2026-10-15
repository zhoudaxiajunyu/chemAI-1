"""认证端点集成测试（tasks 10.1-10.4，FastAPI TestClient）。"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from backend.app.core.database import get_db
from backend.app.core.jwt import TOKEN_TYPE_ACCESS, decode_token
from backend.app.core.security import hash_password
from backend.app.main import create_app
from backend.app.models.enums import ApprovalStatus, TeacherRole
from backend.app.models.identity import Account, Parent
from backend.app.models.organization import Class, Grade, School, Student, Teacher


@pytest.fixture
def ctx(engine):
    test_session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    app = create_app()

    def _override_get_db():
        session = test_session()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as client:
        yield client, test_session


def _seed_school(session) -> int:
    school = School(name="测试中学")
    session.add(school)
    session.flush()
    grade = Grade(name="高一", school_id=school.id)
    session.add(grade)
    session.flush()
    klass = Class(name="高一(1)班", grade_id=grade.id)
    session.add(klass)
    session.flush()
    return klass.id


def _seed_teacher(session, *, username="t01", password="pw123456",
                  status=ApprovalStatus.APPROVED, role="teacher") -> int:
    school = School(name="测试中学")
    session.add(school)
    session.flush()
    teacher = Teacher(name="王老师", school_id=school.id, status=status,
                      role=TeacherRole(role))
    session.add(teacher)
    session.flush()
    session.add(Account(
        username=username, password_hash=hash_password(password),
        role=role, teacher_id=teacher.id,
    ))
    session.commit()
    return teacher.id


def test_teacher_login_success(ctx):
    client, Session = ctx
    with Session() as s:
        teacher_id = _seed_teacher(s)

    r = client.post("/api/auth/login", json={
        "username": "t01", "password": "pw123456", "role": "teacher"
    })
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    assert set(["token", "refresh_token", "user_id", "name", "role"]).issubset(data)
    assert data["user_id"] == teacher_id
    assert data["name"] == "王老师"
    assert data["role"] == "teacher"

    payload = decode_token(data["token"], expected_type=TOKEN_TYPE_ACCESS)
    assert payload["user_id"] == teacher_id
    assert payload["role"] == "teacher"
    assert payload["school_id"] == 1
    assert payload["type"] == "access"
    assert "iat" in payload and "exp" in payload


def test_login_wrong_password_401(ctx, caplog):
    client, Session = ctx
    with Session() as s:
        _seed_teacher(s)

    with caplog.at_level("WARNING"):
        r = client.post("/api/auth/login", json={
            "username": "t01", "password": "WRONG-PASS-999", "role": "teacher"
        })
    assert r.status_code == 401
    assert "WRONG-PASS-999" not in caplog.text  # 日志禁止泄露密码


def test_login_unknown_user_401(ctx):
    client, _ = ctx
    r = client.post("/api/auth/login", json={
        "username": "nobody", "password": "x", "role": "teacher"
    })
    assert r.status_code == 401


def test_login_pending_teacher_401(ctx):
    client, Session = ctx
    with Session() as s:
        _seed_teacher(s, username="pending01", status=ApprovalStatus.PENDING)

    r = client.post("/api/auth/login", json={
        "username": "pending01", "password": "pw123456", "role": "teacher"
    })
    assert r.status_code == 401


def test_login_rejected_teacher_401(ctx):
    client, Session = ctx
    with Session() as s:
        _seed_teacher(s, username="rejected01", status=ApprovalStatus.REJECTED)

    r = client.post("/api/auth/login", json={
        "username": "rejected01", "password": "pw123456", "role": "teacher"
    })
    assert r.status_code == 401


def test_login_role_mismatch_401(ctx):
    client, Session = ctx
    with Session() as s:
        _seed_teacher(s, username="t02")

    r = client.post("/api/auth/login", json={
        "username": "t02", "password": "pw123456", "role": "student"
    })
    assert r.status_code == 401


def test_student_login_resolves_school_id(ctx):
    client, Session = ctx
    with Session() as s:
        class_id = _seed_school(s)
        student = Student(name="李同学", class_id=class_id)
        s.add(student)
        s.flush()
        s.add(Account(
            username="s01", password_hash=hash_password("pw123456"),
            role="student", student_id=student.id,
        ))
        s.commit()
        student_id = student.id

    r = client.post("/api/auth/login", json={
        "username": "s01", "password": "pw123456", "role": "student"
    })
    assert r.status_code == 200
    data = r.json()
    assert data["user_id"] == student_id
    payload = decode_token(data["token"])
    assert payload["role"] == "student"
    assert payload["school_id"] is not None


def test_refresh_success_and_rejects_access_token(ctx):
    client, Session = ctx
    with Session() as s:
        _seed_teacher(s)
    login = client.post("/api/auth/login", json={
        "username": "t01", "password": "pw123456", "role": "teacher"
    }).json()

    # refresh_token 换新 access
    r = client.post("/api/auth/refresh", json={"refresh_token": login["refresh_token"]})
    assert r.status_code == 200
    new_token = r.json()["token"]
    payload = decode_token(new_token, expected_type=TOKEN_TYPE_ACCESS)
    assert payload["user_id"] == login["user_id"]

    # access_token 不能用于刷新端点（类型校验）
    r_bad = client.post("/api/auth/refresh", json={"refresh_token": login["token"]})
    assert r_bad.status_code == 401


def test_parent_login_success_no_school_id(ctx):
    client, Session = ctx
    with Session() as s:
        parent = Parent(name="李家长", phone="13800000001",
                        password_hash=hash_password("pp123456"))
        s.add(parent)
        s.commit()
        parent_id = parent.id

    r = client.post("/api/parent/login", json={
        "phone": "13800000001", "password": "pp123456"
    })
    assert r.status_code == 200
    data = r.json()
    assert data["role"] == "parent"
    assert data["user_id"] == parent_id

    payload = decode_token(data["token"], expected_type=TOKEN_TYPE_ACCESS)
    assert payload["role"] == "parent"
    assert "school_id" not in payload


def test_parent_login_wrong_password_401(ctx):
    client, Session = ctx
    with Session() as s:
        s.add(Parent(name="李家长", phone="13800000002",
                     password_hash=hash_password("pp123456")))
        s.commit()

    r = client.post("/api/parent/login", json={
        "phone": "13800000002", "password": "bad"
    })
    assert r.status_code == 401


def test_parent_account_cannot_use_teacher_channel(ctx):
    client, Session = ctx
    with Session() as s:
        parent = Parent(name="张家长", phone="13800000003",
                        password_hash=hash_password("pp123456"))
        s.add(parent)
        s.flush()
        s.add(Account(
            username="p01", password_hash=hash_password("pp123456"),
            role="parent", parent_id=parent.id,
        ))
        s.commit()

    r = client.post("/api/auth/login", json={
        "username": "p01", "password": "pp123456", "role": "parent"
    })
    assert r.status_code == 401


def test_real_app_middleware_health_docs_and_protection(ctx):
    client, _ = ctx
    assert client.get("/health").status_code == 200
    assert client.get("/docs").status_code == 200
    assert client.get("/openapi.json").status_code == 200
    # 未携带令牌访问受保护路径，中间件先于路由返回 401
    assert client.get("/api/classes").status_code == 401


def test_login_rejects_unknown_fields_and_oversized_input(ctx):
    client, Session = ctx
    with Session() as s:
        _seed_teacher(s, username="t_strict", password="pw123456")

    # 未知字段不再被静默忽略
    r_extra = client.post("/api/auth/login", json={
        "username": "t_strict", "password": "pw123456",
        "role": "teacher", "is_admin": True,
    })
    assert r_extra.status_code == 422

    # 无界输入被拒绝（用户名 / 密码上界）
    assert client.post("/api/auth/login", json={
        "username": "u" * 151, "password": "pw123456", "role": "teacher",
    }).status_code == 422
    assert client.post("/api/auth/login", json={
        "username": "t_strict", "password": "p" * 129, "role": "teacher",
    }).status_code == 422


def test_openapi_declares_bearer_security_scheme(ctx):
    client, _ = ctx
    spec = client.get("/openapi.json").json()
    assert spec["components"]["securitySchemes"]["BearerAuth"] == {
        "type": "http", "scheme": "bearer", "bearerFormat": "JWT",
    }
