"""应用配置（环境变量）。"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # 数据库
    database_url: str = "sqlite:///./chemai.db"

    # JWT（密钥必须由环境变量 JWT_SECRET_KEY 提供；默认值仅供本地开发/测试）
    jwt_secret_key: str = "dev-only-insecure-key-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 24 * 60       # 24 小时
    refresh_token_expire_minutes: int = 7 * 24 * 60  # 7 天


@lru_cache
def get_settings() -> Settings:
    return Settings()
