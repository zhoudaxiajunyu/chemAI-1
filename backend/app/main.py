"""FastAPI 应用装配：认证中间件、权限异常映射、路由注册。"""
import logging

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from backend.app.api.auth import router as auth_router
from backend.app.core.config import get_settings
from backend.app.core.middleware import AuthMiddleware
from backend.app.core.permissions import PermissionDenied

logger = logging.getLogger("chemai")

_DEV_DEFAULT_SECRET = "dev-only-insecure-key-change-me"


def create_app() -> FastAPI:
    settings = get_settings()
    if settings.jwt_secret_key == _DEV_DEFAULT_SECRET:
        logger.warning("JWT_SECRET_KEY 仍为内置开发默认值，生产环境必须通过环境变量覆盖")

    app = FastAPI(title="ChemAI 高中化学 AI 系统", version="0.2.0")

    app.add_middleware(AuthMiddleware)

    @app.exception_handler(PermissionDenied)
    async def permission_denied_handler(_request, exc: PermissionDenied):
        return JSONResponse(status_code=403, content={"detail": str(exc)})

    app.include_router(auth_router)

    @app.get("/health", tags=["system"])
    async def health():
        return {"status": "ok"}

    return app


app = create_app()
