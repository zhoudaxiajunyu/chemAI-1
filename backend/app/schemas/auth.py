"""认证相关 Pydantic schema。"""
from pydantic import BaseModel, ConfigDict, Field

# 输入边界：拒绝无界输入，同时 forbid 未知字段避免参数被静默忽略
_STRICT = ConfigDict(extra="forbid")


class LoginRequest(BaseModel):
    model_config = _STRICT

    username: str = Field(min_length=1, max_length=150)
    password: str = Field(min_length=1, max_length=128)
    role: str = Field(min_length=1, max_length=32)


class ParentLoginRequest(BaseModel):
    model_config = _STRICT

    phone: str = Field(min_length=1, max_length=20)
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    success: bool
    token: str
    refresh_token: str
    user_id: int
    name: str
    role: str


class RefreshRequest(BaseModel):
    model_config = _STRICT

    refresh_token: str = Field(min_length=1, max_length=4096)


class RefreshResponse(BaseModel):
    success: bool
    token: str
