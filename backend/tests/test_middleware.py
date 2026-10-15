"""认证中间件测试（tasks 9.3 五场景）。"""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from jose import jwt as jose_jwt

from backend.app.core.config import get_settings
from backend.app.core.middleware import AuthMiddleware, is_whitelisted
from backend.app.core.jwt import create_access_token
from backend.app.core.permissions import TEACHER


@pytest.fixture
def client():
    app = FastAPI()
    app.add_middleware(AuthMiddleware)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.post("/api/parent/login")
    def parent_login():
        return {"success": True}

    @app.get("/api/parent/children")
    def children():
        return []

    @app.get("/api/classes")
    def classes(request: Request):
        return {"role": request.state.user.role}

    return TestClient(app)


def test_whitelist_helper():
    assert is_whitelisted("/health")
    assert is_whitelisted("/api/auth/login")
    assert is_whitelisted("/api/parent/login")
    assert not is_whitelisted("/api/parent/children")


def test_health_passes_without_token(client):
    assert client.get("/health").status_code == 200


def test_parent_login_exact_path_passes_without_token(client):
    # 不被中间件 401 拦截（进入端点逻辑，端点自身决定 200/401）
    r = client.post("/api/parent/login")
    assert r.status_code == 200


def test_parent_business_path_without_token_401(client):
    assert client.get("/api/parent/children").status_code == 401


def test_protected_path_without_token_401(client):
    assert client.get("/api/classes").status_code == 401


def test_valid_token_reaches_route(client):
    token = create_access_token(1, TEACHER, school_id=9)
    r = client.get("/api/classes", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["role"] == TEACHER


def test_expired_token_401(client):
    settings = get_settings()
    past = datetime.now(timezone.utc) - timedelta(minutes=1)
    token = jose_jwt.encode(
        {"sub": "1", "user_id": 1, "role": TEACHER, "school_id": 1,
         "type": "access", "iat": past - timedelta(hours=25), "exp": past},
        settings.jwt_secret_key, algorithm=settings.jwt_algorithm,
    )
    r = client.get("/api/classes", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401


def test_tampered_token_401(client):
    token = create_access_token(1, TEACHER, school_id=1)
    tampered = token[:-4] + ("xxxx" if not token.endswith("xxxx") else "yyyy")
    r = client.get("/api/classes", headers={"Authorization": f"Bearer {tampered}"})
    assert r.status_code == 401
