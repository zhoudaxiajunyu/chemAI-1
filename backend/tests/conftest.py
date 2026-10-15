"""pytest 基建：SQLite 内存库（开启 FK 约束）+ 每测试独立建表。"""
import os

# 必须在导入应用模块前设置测试密钥
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-do-not-use-in-prod")

import pytest  # noqa: E402
from sqlalchemy import create_engine, event  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from backend.app.core.database import configure_sqlite_pragmas  # noqa: E402
from backend.app.models.base import Base  # noqa: E402
import backend.app.models  # noqa: E402,F401  导入模型包以注册全部模型到 metadata


@pytest.fixture
def engine():
    """每个测试一个全新内存库；StaticPool 保证多会话共享同一连接。"""
    eng = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(eng, "connect")
    def _enable_fk(dbapi_connection, _):  # noqa: ANN001
        configure_sqlite_pragmas(dbapi_connection, _, journal_wal=False)

    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)
    eng.dispose()


@pytest.fixture
def db_session(engine):
    session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)()
    try:
        yield session
    finally:
        session.close()
