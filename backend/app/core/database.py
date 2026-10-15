"""数据库引擎工厂与会话（应用与测试共用，保证 JSON 反序列化行为一致）。"""
from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from backend.app.core.config import get_settings


def configure_sqlite_pragmas(dbapi_connection, _, *, journal_wal: bool) -> None:
    """SQLite 连接级 PRAGMA：外键强制开启（默认关闭）；文件库启用 WAL。

    应用工厂与测试引擎共用此函数，避免两处配置漂移。
    """
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    if journal_wal:
        cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()


def make_engine(url: str | None = None, *, echo: bool = False) -> Engine:
    """创建引擎；SQLite 自动打开外键约束，文件库启用 WAL。"""
    settings = get_settings()
    resolved_url = url or settings.database_url
    is_sqlite = resolved_url.startswith("sqlite")
    engine = create_engine(
        resolved_url,
        echo=echo,
        connect_args={"check_same_thread": False} if is_sqlite else {},
    )
    if is_sqlite:
        # 内存库不能开 WAL（journal_mode 会回退为 memory）
        memory = engine.url.database in (None, ":memory:")

        @event.listens_for(engine, "connect")
        def _apply_pragmas(dbapi_connection, _):  # noqa: ANN001
            configure_sqlite_pragmas(dbapi_connection, _, journal_wal=not memory)

    return engine


engine = make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """FastAPI 依赖：提供请求级会话。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
