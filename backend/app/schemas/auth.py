"""认证相关 Pydantic schema。"""
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)
    role: str = Field(min_length=1)


class ParentLoginRequest(BaseModel):
    phone: str = Field(min_length=1)
    password: str = Field(min_length=1)


class TokenResponse(BaseModel):
    success: bool
    token: str
    refresh_token: str
    user_id: int
    name: str
    role: str


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class RefreshResponse(BaseModel):
    success: bool
    token: str
