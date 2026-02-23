"""
安全工具：密码哈希和验证
"""
import bcrypt

# bcrypt 最大密码长度
BCRYPT_MAX_PASSWORD_LENGTH = 72


def hash_password(password: str) -> str:
    """哈希密码"""
    # bcrypt 限制密码最长 72 字节
    password_bytes = password.encode('utf-8')[:BCRYPT_MAX_PASSWORD_LENGTH]
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    # bcrypt 限制密码最长 72 字节
    password_bytes = plain_password.encode('utf-8')[:BCRYPT_MAX_PASSWORD_LENGTH]
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_bytes)
