"""认证端点：教师/学生登录、刷新令牌、家长独立登录通道。"""
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.jwt import (
    TOKEN_TYPE_REFRESH,
    TokenValidationError,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from backend.app.core.security import verify_password
from backend.app.models.enums import ApprovalStatus
from backend.app.models.identity import Account, Parent
from backend.app.models.organization import Student, Teacher
from backend.app.schemas.auth import (
    LoginRequest,
    ParentLoginRequest,
    RefreshRequest,
    RefreshResponse,
    TokenResponse,
)

logger = logging.getLogger("chemai.auth")

router = APIRouter(tags=["auth"])

_INVALID_CREDENTIALS = "用户名或密码错误"
_ACCOUNT_NOT_APPROVED = "账号尚未通过审核"


def _issue_tokens(user_id: int, role: str, school_id: int | None) -> tuple[str, str]:
    return (
        create_access_token(user_id, role, school_id),
        create_refresh_token(user_id, role, school_id),
    )


@router.post("/api/auth/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """教师/学生统一登录（家长走 /api/parent/login 独立通道）。"""
    account = (
        db.query(Account).filter(Account.username == body.username).first()
    )

    # 统一错误信息，避免账号枚举；日志禁止记录密码
    if account is None or not verify_password(body.password, account.password_hash):
        logger.warning(
            "登录失败: 凭据无效 username=%s role_hint=%s", body.username, body.role
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_INVALID_CREDENTIALS)

    # 角色必须与账户快照一致；家长账户不得使用本通道
    if account.role == "parent" or body.role != account.role:
        logger.warning(
            "登录失败: 角色不匹配 username=%s requested=%s actual=%s",
            body.username, body.role, account.role,
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_INVALID_CREDENTIALS)

    name: str
    school_id: int | None

    if account.teacher_id is not None:
        teacher = db.get(Teacher, account.teacher_id)
        if teacher is None or teacher.status != ApprovalStatus.APPROVED:
            logger.warning(
                "登录被拒: 教师账号未通过审核 account_id=%s status=%s",
                account.id, None if teacher is None else teacher.status.value,
            )
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_ACCOUNT_NOT_APPROVED)
        name = teacher.name
        school_id = teacher.school_id
    elif account.student_id is not None:
        student = db.get(Student, account.student_id)
        if student is None or student.status != ApprovalStatus.APPROVED:
            logger.warning("登录被拒: 学生账号未通过审核 account_id=%s", account.id)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_ACCOUNT_NOT_APPROVED)
        name = student.name
        school_id = student.class_.grade.school_id
    else:
        # 理论上 CHECK 约束保证 parent_id 非空——家长通道之外一律拒绝
        logger.warning("登录失败: 不支持的账户类型 account_id=%s", account.id)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_INVALID_CREDENTIALS)

    subject_id = account.teacher_id if account.teacher_id is not None else account.student_id
    access, refresh = _issue_tokens(subject_id, account.role, school_id)
    logger.info("登录成功 user_id=%s role=%s", subject_id, account.role)
    return TokenResponse(
        success=True,
        token=access,
        refresh_token=refresh,
        user_id=subject_id,
        name=name,
        role=account.role,
    )


@router.post("/api/auth/refresh", response_model=RefreshResponse)
def refresh_token(body: RefreshRequest) -> RefreshResponse:
    """以 refresh_token 换取新 access_token；access_token 不得用于本端点。"""
    try:
        payload = decode_token(body.refresh_token, expected_type=TOKEN_TYPE_REFRESH)
    except TokenValidationError as exc:
        logger.warning("刷新令牌失败: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="刷新令牌无效或已过期"
        ) from exc

    new_access = create_access_token(
        payload["user_id"], payload["role"], payload.get("school_id")
    )
    return RefreshResponse(success=True, token=new_access)


@router.post("/api/parent/login", response_model=TokenResponse)
def parent_login(body: ParentLoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """家长独立认证通道：手机号 + 密码，令牌不携带 school_id。"""
    parent = db.query(Parent).filter(Parent.phone == body.phone).first()
    if (
        parent is None
        or parent.password_hash is None
        or not verify_password(body.password, parent.password_hash)
    ):
        logger.warning("家长登录失败: 凭据无效 phone=%s", body.phone)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_INVALID_CREDENTIALS)

    access, refresh = _issue_tokens(parent.id, "parent", None)
    logger.info("家长登录成功 parent_id=%s", parent.id)
    return TokenResponse(
        success=True,
        token=access,
        refresh_token=refresh,
        user_id=parent.id,
        name=parent.name,
        role="parent",
    )
