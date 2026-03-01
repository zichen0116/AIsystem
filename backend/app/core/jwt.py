"""
JWT 令牌工具
"""
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from app.core.config import settings


def create_access_token(user_id: int, token_version: int = 1) -> str:
    """创建访问令牌

    Args:
        user_id: 用户ID
        token_version: Token 版本号，用于修改密码后使旧token失效
    """
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode = {
        "sub": str(user_id),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "version": token_version
    }
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """解码访问令牌，返回 user_id 和 token_version

    Returns:
        {"user_id": int, "version": int} 或 None
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        user_id = payload.get("sub")
        if user_id is None:
            return None
        version = payload.get("version", 1)
        return {
            "user_id": int(user_id),
            "version": version
        }
    except (JWTError, ValueError):
        return None


def get_token_expired_at(token: str) -> Optional[datetime]:
    """获取 token 的过期时间"""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_exp": False}
        )
        exp = payload.get("exp")
        if exp:
            return datetime.fromtimestamp(exp, tz=timezone.utc)
        return None
    except (JWTError, ValueError):
        return None


def token_to_hash(token: str) -> str:
    """将 token 转为 SHA256 哈希（用于黑名单存储）"""
    return hashlib.sha256(token.encode()).hexdigest()
