"""
认证路由
"""
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import hash_password, verify_password
from app.core.jwt import (
    create_access_token, token_to_hash, get_token_expired_at,
    create_2fa_pending_token, decode_2fa_pending_token,
)
from app.core.auth import CurrentUser
from app.models.user import User
from app.models.token_blacklist import TokenBlacklist
from app.schemas.auth import (
    UserRegister, UserLogin, LoginResponse, UserResponse,
    ChangePassword, SendCodeRequest,
    UpdateProfile, ChangePhone, ChangeEmail, Toggle2FA,
    TwoFARequired, Login2FAVerify, SendEmailCodeRequest,
)
from app.services.sms import send_sms_code, verify_sms_code
from app.services.email import send_email_code, verify_email_code

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/send-code", status_code=status.HTTP_200_OK)
async def send_code(data: SendCodeRequest):
    """发送短信验证码"""
    try:
        await send_sms_code(data.phone)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(e)
        )
    return {"message": "验证码已发送"}


@router.post("/register", response_model=LoginResponse, status_code=status.HTTP_201_CREATED)
async def register(
    data: UserRegister,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """用户注册"""
    result = await db.execute(
        select(User).where(User.phone == data.phone)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="手机号已被注册"
        )

    if not await verify_sms_code(data.phone, data.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="验证码错误或已过期"
        )

    user = User(
        phone=data.phone,
        password_hash=hash_password(data.password),
        full_name=data.full_name or "user"
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    access_token = create_access_token(user.id, user.token_version)
    return LoginResponse(
        access_token=access_token,
        user=UserResponse.model_validate(user),
    )


@router.post("/login")
async def login(
    data: UserLogin,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """用户登录；若启用 2FA 则返回 202 + TwoFARequired，否则返回 200 + LoginResponse"""
    result = await db.execute(
        select(User).where(User.phone == data.phone)
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="手机号或密码错误"
        )

    if user.two_fa_enabled and user.email:
        temp_token = create_2fa_pending_token(user.id)
        # 发送验证码到绑定邮箱
        await send_email_code(user.email)
        email = user.email
        at_idx = email.find("@")
        masked = email[:2] + "***" + email[at_idx:] if at_idx > 2 else "***" + email[at_idx:]
        return Response(
            content=TwoFARequired(
                requires_2fa=True,
                temp_token=temp_token,
                masked_email=masked,
            ).model_dump_json(),
            status_code=status.HTTP_202_ACCEPTED,
            media_type="application/json",
        )

    access_token = create_access_token(user.id, user.token_version)
    return LoginResponse(
        access_token=access_token,
        user=UserResponse.model_validate(user),
    )


@router.post("/login/2fa", response_model=LoginResponse)
async def login_2fa(
    data: Login2FAVerify,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """2FA 二次验证，校验邮箱验证码后颁发正式 token"""
    payload = decode_2fa_pending_token(data.temp_token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="临时令牌无效或已过期"
        )

    user_id = payload["user_id"]
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在"
        )

    if not await verify_email_code(user.email, data.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="验证码错误或已过期"
        )

    access_token = create_access_token(user.id, user.token_version)
    return LoginResponse(
        access_token=access_token,
        user=UserResponse.model_validate(user),
    )


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    request: Request,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """退出登录（将当前 token 加入黑名单）"""
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:]
        expired_at = get_token_expired_at(token)
        if expired_at:
            token_hash = token_to_hash(token)
            existing = await db.execute(
                select(TokenBlacklist).where(TokenBlacklist.token_hash == token_hash)
            )
            if existing.scalar_one_or_none() is None:
                blacklist_entry = TokenBlacklist(
                    token_hash=token_hash,
                    expired_at=expired_at
                )
                db.add(blacklist_entry)
                await db.commit()

    return {"message": "退出成功"}


@router.put("/change-password", status_code=status.HTTP_200_OK)
async def change_password(
    data: ChangePassword,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """修改密码（会使所有旧 token 失效）"""
    if not verify_password(data.old_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="旧密码错误"
        )

    current_user.password_hash = hash_password(data.new_password)
    current_user.token_version += 1
    await db.commit()

    return {"message": "密码修改成功，请重新登录"}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: CurrentUser):
    """获取当前用户信息"""
    return current_user


@router.put("/profile", response_model=UserResponse)
async def update_profile(
    data: UpdateProfile,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """更新个人资料"""
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(current_user, field, value)
    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.put("/change-phone", status_code=status.HTTP_200_OK)
async def change_phone(
    data: ChangePhone,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """修改手机号（需短信验证码）"""
    if not await verify_sms_code(data.new_phone, data.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="验证码错误或已过期"
        )

    existing = await db.execute(
        select(User).where(User.phone == data.new_phone)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该手机号已被使用"
        )

    current_user.phone = data.new_phone
    await db.commit()
    return {"message": "手机号修改成功"}


@router.put("/change-email", status_code=status.HTTP_200_OK)
async def change_email(
    data: ChangeEmail,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """修改邮箱（直接修改，无需验证）"""
    existing = await db.execute(
        select(User).where(User.email == data.new_email)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该邮箱已被使用"
        )

    current_user.email = data.new_email
    await db.commit()
    return {"message": "邮箱修改成功"}


@router.post("/send-email-code", status_code=status.HTTP_200_OK)
async def send_email_code_route(
    current_user: CurrentUser,
):
    """向当前用户绑定邮箱发送验证码（用于开启 2FA）"""
    if not current_user.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请先绑定邮箱"
        )
    result = await send_email_code(current_user.email)
    if not result["ok"]:
        wait = result.get("wait", 60)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"请等待 {wait} 秒后再试"
        )
    return {"message": "验证码已发送"}


@router.put("/toggle-2fa", status_code=status.HTTP_200_OK)
async def toggle_2fa(
    data: Toggle2FA,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """开启或关闭 2FA"""
    if data.enable:
        if not current_user.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="请先绑定邮箱"
            )
        if not data.code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="开启 2FA 需要提供邮箱验证码"
            )
        if not await verify_email_code(current_user.email, data.code):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="验证码错误或已过期"
            )

    current_user.two_fa_enabled = data.enable
    await db.commit()
    state = "开启" if data.enable else "关闭"
    return {"message": f"2FA 已{state}"}
