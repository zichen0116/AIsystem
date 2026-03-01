"""
认证路由
"""
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import hash_password, verify_password
from app.core.jwt import create_access_token, token_to_hash, get_token_expired_at
from app.core.auth import CurrentUser
from app.models.user import User
from app.models.token_blacklist import TokenBlacklist
from app.schemas.auth import UserRegister, UserLogin, TokenResponse, UserResponse, ChangePassword

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    data: UserRegister,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """用户注册"""
    # 检查手机号是否已存在
    result = await db.execute(
        select(User).where(User.phone == data.phone)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="手机号已被注册"
        )

    # 创建新用户（id 自增）
    user = User(
        phone=data.phone,
        password_hash=hash_password(data.password),
        full_name=data.full_name
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # 生成令牌（带 token_version）
    access_token = create_access_token(user.id, user.token_version)
    return TokenResponse(access_token=access_token)


@router.post("/login", response_model=TokenResponse)
async def login(
    data: UserLogin,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """用户登录"""
    # 查询用户
    result = await db.execute(
        select(User).where(User.phone == data.phone)
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="手机号或密码错误"
        )

    # 生成令牌（带 token_version）
    access_token = create_access_token(user.id, user.token_version)
    return TokenResponse(access_token=access_token)


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    request: Request,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """退出登录（将当前 token 加入黑名单）"""
    # 从请求头获取 token
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:]  # 去掉 "Bearer " 前缀

        # 获取 token 过期时间
        expired_at = get_token_expired_at(token)
        if expired_at:
            # 存入黑名单
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
    # 验证旧密码
    if not verify_password(data.old_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="旧密码错误"
        )

    # 更新密码并增加 token_version
    current_user.password_hash = hash_password(data.new_password)
    current_user.token_version += 1

    await db.commit()

    return {"message": "密码修改成功，请重新登录"}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: CurrentUser):
    """获取当前用户信息"""
    return current_user
