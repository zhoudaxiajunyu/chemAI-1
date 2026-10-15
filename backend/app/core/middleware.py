"""JWT 认证中间件：白名单 + Bearer 校验，失败统一 401。"""
import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from backend.app.core.jwt import TOKEN_TYPE_ACCESS, TokenValidationError, decode_token
from backend.app.core.permissions import UserContext

logger = logging.getLogger("chemai.auth")

# 前缀白名单（整个前缀放行）
PREFIX_WHITELIST = ("/api/auth/",)

# 精确白名单（只放行这一个路径，避免 /api/parent/ 整体暴露）
EXACT_WHITELIST = frozenset({
    "/api/parent/login",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/health",
})


def is_whitelisted(path: str) -> bool:
    if path in EXACT_WHITELIST:
        return True
    return any(path.startswith(prefix) for prefix in PREFIX_WHITELIST)


def _unauthorized(detail: str) -> JSONResponse:
    return JSONResponse(status_code=401, content={"detail": detail})


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        if not path.startswith("/api/") or is_whitelisted(path):
            return await call_next(request)

        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            logger.warning("认证拒绝: 缺失或格式错误的 Authorization 头 path=%s", path)
            return _unauthorized("缺少有效的认证令牌")

        token = header[len("Bearer "):].strip()
        try:
            payload = decode_token(token, expected_type=TOKEN_TYPE_ACCESS)
            # 签名有效但声明缺失/畸形同样按未认证处理，不能让 KeyError 漏成 500
            user = UserContext(
                user_id=int(payload["user_id"]),
                role=payload["role"],
                school_id=payload.get("school_id"),
            )
        except (TokenValidationError, KeyError, TypeError, ValueError) as exc:
            logger.warning("认证拒绝: 令牌校验失败 path=%s reason=%s", path, exc)
            return _unauthorized("认证令牌无效或已过期")

        request.state.user = user
        return await call_next(request)
