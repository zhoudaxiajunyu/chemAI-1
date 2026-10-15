"""FastAPI 应用装配：认证中间件、权限异常映射、路由注册。"""
import logging

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse

from backend.app.api.auth import router as auth_router
from backend.app.core.config import get_settings
from backend.app.core.middleware import AuthMiddleware, is_whitelisted
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

    def _custom_openapi():
        """声明 Bearer 安全方案，使 /docs 的 Authorize 与 Try-it-out 可用。

        认证由中间件而非路由依赖实现，OpenAPI 无法自动推导；此处与
        is_whitelisted 同源，只有真正受保护的路径才标记需要 Bearer。
        """
        if app.openapi_schema:
            return app.openapi_schema
        schema = get_openapi(title=app.title, version=app.version, routes=app.routes)
        security_schemes = schema.setdefault("components", {}).setdefault(
            "securitySchemes", {}
        )
        security_schemes["BearerAuth"] = {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
        for path, operations in schema.get("paths", {}).items():
            if not path.startswith("/api/") or is_whitelisted(path):
                continue
            for operation in operations.values():
                operation.setdefault("security", [{"BearerAuth": []}])
        app.openapi_schema = schema
        return schema

    app.openapi = _custom_openapi
    return app


app = create_app()
