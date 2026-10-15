"""SQLAlchemy 声明式基类与统一 metadata。

所有模型必须继承此 Base，保证 Alembic autogenerate 使用单一 metadata 源。
"""
import enum

from sqlalchemy import Enum as SAEnum, MetaData
from sqlalchemy.orm import DeclarativeBase


def sqlite_enum(enum_cls: type[enum.Enum], *, name: str) -> SAEnum:
    """枚举列工厂（全项目统一）。

    - native_enum=False：SQLite 落为 VARCHAR
    - create_constraint=True：DB 层生成 CHECK（裸 SQL 写非法值也拒绝）
    - values_callable：入库值用 .value（小写 code）而非 .name
    """
    return SAEnum(
        enum_cls,
        native_enum=False,
        create_constraint=True,
        values_callable=lambda members: [m.value for m in members],
        name=name,
    )

# 显式约束命名，保证 Alembic autogenerate 产出稳定、可预测的名字
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
