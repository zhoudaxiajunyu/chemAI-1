"""Alembic 迁移往返测试（tasks 11.4-11.5）：
upgrade head 建出与 metadata 一致的 24 张表；downgrade base 清空；再 upgrade 复建。
"""
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

from backend.app.models.base import Base

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_INI = PROJECT_ROOT / "alembic.ini"
EXPECTED_TABLES = set(Base.metadata.tables)


@pytest.fixture
def alembic_cfg(tmp_path, monkeypatch):
    # 确保 env.py 取测试专用库，而非进程环境里的 DATABASE_URL
    monkeypatch.delenv("DATABASE_URL", raising=False)
    db_path = tmp_path / "migration_test.db"
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path.as_posix()}")
    return cfg


def _table_names(db_file: Path) -> set[str]:
    engine = create_engine(f"sqlite:///{db_file.as_posix()}")
    try:
        return set(inspect(engine).get_table_names())
    finally:
        engine.dispose()


def test_upgrade_downgrade_roundtrip(alembic_cfg, tmp_path):
    db_file = tmp_path / "migration_test.db"

    # 1) 空库 upgrade head → 24 张表，与 ORM metadata 完全一致
    command.upgrade(alembic_cfg, "head")
    tables = _table_names(db_file) - {"alembic_version"}
    assert tables == EXPECTED_TABLES
    assert len(tables) == 24

    # 2) CHECK 约束随迁移落地：账户三选一 + 复习等级范围
    engine = create_engine(f"sqlite:///{db_file.as_posix()}")
    with engine.connect() as conn:
        ddl = {
            name: sql
            for name, sql in conn.execute(
                text("SELECT name, sql FROM sqlite_master WHERE type='table'")
            ).all()
        }
    engine.dispose()
    assert "single_subject_fk" in ddl["accounts"]
    assert "level BETWEEN 0 AND 5" in ddl["review_tasks"]
    # 枚举 CHECK 落为小写 code（非枚举名）
    assert "'pending'" in ddl["teachers"] and "'approved'" in ddl["teachers"]

    # 3) downgrade base → 业务表全部消失
    command.downgrade(alembic_cfg, "base")
    assert _table_names(db_file) - {"alembic_version"} == set()

    # 4) 再 upgrade head → 24 张表复建（幂等可重入）
    command.upgrade(alembic_cfg, "head")
    assert len(_table_names(db_file) - {"alembic_version"}) == 24

    # 5) 迁移建出的库上，裸 SQL 写入非法枚举值同样被 CHECK 拒绝
    engine = create_engine(f"sqlite:///{db_file.as_posix()}")
    with engine.connect() as conn:
        with pytest.raises(IntegrityError, match="ck_questions_question_difficulty"):
            conn.execute(text(
                "INSERT INTO questions (stem, difficulty) VALUES ('x', 'bogus')"
            ))
            conn.commit()
    engine.dispose()
