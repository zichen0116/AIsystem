"""
认证依赖函数
"""
from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.jwt import decode_access_token, token_to_hash
from app.models.user import User
from app.models.token_blacklist import TokenBlacklist

# Bearer token 认证
security = HTTPBearer()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> User:
    """获取当前认证用户"""
    token = credentials.credentials

    # 解码 token
    token_data = decode_access_token(token)
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = token_data["user_id"]
    token_version = token_data["version"]

    # 检查黑名单
    token_hash = token_to_hash(token)
    result = await db.execute(
        select(TokenBlacklist).where(TokenBlacklist.token_hash == token_hash)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌已失效，请重新登录",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 查询用户
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 检查 token 版本号（修改密码后所有设备下线）
    if user.token_version != token_version:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="密码已修改，请重新登录",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


# 类型别名
CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_admin_user(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """要求当前用户为管理员"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    return current_user


# 管理员类型别名
AdminUser = Annotated[User, Depends(get_admin_user)]
