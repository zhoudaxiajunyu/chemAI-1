"""JWT 与密码安全测试（tasks 8.1-8.2）。"""
from datetime import timedelta

import pytest
from jose import jwt

from backend.app.core.config import get_settings
from backend.app.core.jwt import (
    TOKEN_TYPE_ACCESS,
    TOKEN_TYPE_REFRESH,
    TokenValidationError,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from backend.app.core.security import hash_password, verify_password


# ---------- 8.1 bcrypt ----------

def test_bcrypt_hash_and_verify():
    h = hash_password("S3cret!")
    assert h != "S3cret!"
    assert verify_password("S3cret!", h) is True
    assert verify_password("wrong", h) is False


def test_bcrypt_long_multibyte_password_roundtrip():
    # 120 字节（"化" × 40，每字 3 字节），跨越 72 字节边界：
    # 哈希与校验必须共用同一截断归一化，否则边界处多字节字符导致验签失败
    long_pw = "化" * 40
    h = hash_password(long_pw)
    assert verify_password(long_pw, h) is True
    # 错误口令在前 72 字节内就不同（首字不同），必须验签失败
    assert verify_password("错" + "化" * 39, h) is False


# ---------- 8.2 JWT ----------

def test_jwt_roundtrip_claims():
    token = create_access_token(user_id=42, role="teacher", school_id=7)
    payload = decode_token(token, expected_type=TOKEN_TYPE_ACCESS)
    assert payload["user_id"] == 42
    assert payload["sub"] == "42"
    assert payload["role"] == "teacher"
    assert payload["school_id"] == 7
    assert payload["type"] == "access"
    delta_minutes = (payload["exp"] - payload["iat"]) / 60
    assert abs(delta_minutes - 24 * 60) < 1  # 24h（秒级误差容忍）


def test_refresh_token_lifetime():
    token = create_refresh_token(user_id=1, role="admin", school_id=1)
    payload = decode_token(token, expected_type=TOKEN_TYPE_REFRESH)
    delta_days = (payload["exp"] - payload["iat"]) / 86400
    assert abs(delta_days - 7) < 0.001


def test_jwt_tampered_signature_rejected():
    token = create_access_token(1, "teacher", school_id=1)
    tampered = token[:-3] + ("aaa" if not token.endswith("aaa") else "bbb")
    with pytest.raises(TokenValidationError):
        decode_token(tampered)


def test_jwt_expired_rejected():
    # 手工构造一个已过期令牌
    settings = get_settings()
    from datetime import datetime, timezone
    past = datetime.now(timezone.utc) - timedelta(minutes=1)
    raw = jwt.encode(
        {"sub": "1", "user_id": 1, "role": "teacher", "type": "access",
         "iat": past - timedelta(hours=25), "exp": past},
        settings.jwt_secret_key, algorithm=settings.jwt_algorithm,
    )
    with pytest.raises(TokenValidationError):
        decode_token(raw)


def test_jwt_wrong_type_rejected():
    access = create_access_token(1, "teacher", school_id=1)
    with pytest.raises(TokenValidationError):
        decode_token(access, expected_type=TOKEN_TYPE_REFRESH)


def test_parent_token_has_no_school_id():
    token = create_access_token(user_id=9, role="parent")
    payload = decode_token(token, expected_type=TOKEN_TYPE_ACCESS)
    assert payload["role"] == "parent"
    assert "school_id" not in payload
