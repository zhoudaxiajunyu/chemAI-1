"""Alembic 迁移环境：URL 来自应用配置（DATABASE_URL 可覆盖），metadata 取全部模型。"""
import os
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool

from alembic import context

# 保证从项目根目录导入 backend.*（prepend_sys_path=. 已配置，此处为直接执行兜底）
# env.py 位于 <root>/backend/alembic/env.py
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.core.config import get_settings  # noqa: E402
from backend.app.models.base import Base  # noqa: E402
import backend.app.models  # noqa: E402,F401  导入模型包以注册全部 24 张表

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# URL 优先级：显式注入（测试/编程式 Config）> 环境变量 DATABASE_URL > .env/默认值 > ini 占位
_current_url = config.get_main_option("sqlalchemy.url")
_env_url = os.environ.get("DATABASE_URL")
if _env_url:
    config.set_main_option("sqlalchemy.url", _env_url)
elif not _current_url or _current_url.startswith("driver://"):
    config.set_main_option("sqlalchemy.url", get_settings().database_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=url.startswith("sqlite"),
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        is_sqlite = connection.dialect.name == "sqlite"
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=is_sqlite,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
