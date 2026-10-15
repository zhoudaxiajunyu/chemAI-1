"""JWT 签发与校验（python-jose，HS256）。"""
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt

from backend.app.core.config import get_settings

TOKEN_TYPE_ACCESS = "access"
TOKEN_TYPE_REFRESH = "refresh"


class TokenValidationError(Exception):
    """令牌无效、过期、签名错误或类型不匹配。"""


def _create_token(
    subject: str,
    role: str,
    token_type: str,
    expires_delta: timedelta,
    school_id: int | None = None,
) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "user_id": int(subject),
        "role": role,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    # 家长角色不携带 school_id；其他角色必须携带
    if school_id is not None:
        payload["school_id"] = school_id
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(user_id: int, role: str, school_id: int | None = None) -> str:
    settings = get_settings()
    return _create_token(
        str(user_id), role, TOKEN_TYPE_ACCESS,
        timedelta(minutes=settings.access_token_expire_minutes),
        school_id=school_id,
    )


def create_refresh_token(user_id: int, role: str, school_id: int | None = None) -> str:
    settings = get_settings()
    return _create_token(
        str(user_id), role, TOKEN_TYPE_REFRESH,
        timedelta(minutes=settings.refresh_token_expire_minutes),
        school_id=school_id,
    )


def decode_token(token: str, expected_type: str | None = None) -> dict[str, Any]:
    """解码并校验签名/过期；expected_type 非空时强制令牌类型匹配。"""
    settings = get_settings()
    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
    except JWTError as exc:
        raise TokenValidationError(str(exc)) from exc
    if expected_type is not None and payload.get("type") != expected_type:
        raise TokenValidationError(
            f"令牌类型不匹配: 期望 {expected_type}, 实际 {payload.get('type')}"
        )
    return payload
