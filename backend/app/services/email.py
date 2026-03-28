"""
邮件服务：QQ SMTP 发送验证码 + Redis 存储
"""
import smtplib
import random
import string
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
from functools import partial

import redis.asyncio as aioredis

from app.core.config import settings

# Redis key 前缀
_CODE_PREFIX = "email_code:"
_COOLDOWN_PREFIX = "email_cooldown:"
_CODE_TTL = 300   # 5 分钟
_COOLDOWN_TTL = 60  # 60 秒冷却


def _get_redis() -> aioredis.Redis:
    return aioredis.from_url(settings.REDIS_URL, decode_responses=True)


def _generate_code(length: int = 6) -> str:
    return "".join(random.choices(string.digits, k=length))


def _send_smtp(to_email: str, subject: str, body: str) -> None:
    """同步 SMTP 发送，在 executor 中调用以避免阻塞事件循环"""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = formataddr((settings.EMAIL_FROM_NAME, settings.EMAIL_SMTP_USER))
    msg["To"] = to_email
    msg.attach(MIMEText(body, "plain", "utf-8"))

    with smtplib.SMTP(settings.EMAIL_SMTP_HOST, settings.EMAIL_SMTP_PORT, timeout=15) as server:
        server.ehlo()
        server.starttls()
        server.login(settings.EMAIL_SMTP_USER, settings.EMAIL_SMTP_PASSWORD)
        server.sendmail(settings.EMAIL_SMTP_USER, [to_email], msg.as_string())


async def send_email_code(email: str) -> dict:
    """
    向指定邮箱发送 6 位验证码。
    返回 {"ok": True} 或 {"ok": False, "reason": "cooldown"}
    """
    async with _get_redis() as r:
        cooldown_key = f"{_COOLDOWN_PREFIX}{email}"
        if await r.exists(cooldown_key):
            ttl = await r.ttl(cooldown_key)
            return {"ok": False, "reason": "cooldown", "wait": ttl}

        code = _generate_code()
        code_key = f"{_CODE_PREFIX}{email}"
        await r.setex(code_key, _CODE_TTL, code)
        await r.setex(cooldown_key, _COOLDOWN_TTL, "1")

    subject = f"【{settings.EMAIL_FROM_NAME}】您的验证码"
    body = (
        f"您好，\n\n"
        f"您的验证码为：{code}\n\n"
        f"验证码 {_CODE_TTL // 60} 分钟内有效，请勿泄露给他人。\n\n"
        f"{settings.EMAIL_FROM_NAME}"
    )

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, partial(_send_smtp, email, subject, body))
    return {"ok": True}


async def verify_email_code(email: str, code: str) -> bool:
    """校验验证码，通过后删除（一次性）"""
    async with _get_redis() as r:
        code_key = f"{_CODE_PREFIX}{email}"
        stored = await r.get(code_key)
        if stored and stored == code:
            await r.delete(code_key)
            return True
        return False
