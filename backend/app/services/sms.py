"""
短信验证码服务
- 调用国阳云 SMS API 发送验证码
- Redis 存储验证码（5分钟过期、60秒冷却）
"""
import random
import httpx
import redis.asyncio as aioredis

from app.core.config import settings

# Redis 连接（懒初始化）
_redis: aioredis.Redis | None = None

# 短信 API 配置
SMS_API_URL = "https://gyytz.market.alicloudapi.com/sms/smsSend"
SMS_SIGN_ID = "2e65b1bb3d054466b82f0c9d125465e2"
SMS_TEMPLATE_ID = "908e94ccf08b4476ba6c876d13f084ad"

# 验证码参数
CODE_LENGTH = 6
CODE_EXPIRE_SECONDS = 300  # 5 分钟
COOLDOWN_SECONDS = 60  # 冷却 60 秒


def _redis_key(phone: str) -> str:
    return f"sms:code:{phone}"


def _cooldown_key(phone: str) -> str:
    return f"sms:cooldown:{phone}"


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis


def _generate_code() -> str:
    return "".join([str(random.randint(0, 9)) for _ in range(CODE_LENGTH)])


async def send_sms_code(phone: str) -> None:
    """发送短信验证码

    Raises:
        ValueError: 冷却中 / 发送失败
    """
    r = await get_redis()

    # 检查冷却
    if await r.exists(_cooldown_key(phone)):
        ttl = await r.ttl(_cooldown_key(phone))
        raise ValueError(f"发送太频繁，请 {ttl} 秒后重试")

    code = _generate_code()

    # 调用短信 API
    params = {
        "mobile": phone,
        "smsSignId": SMS_SIGN_ID,
        "templateId": SMS_TEMPLATE_ID,
        "param": f"**code**:{code},**minute**:5",
    }
    headers = {
        "Authorization": f"APPCODE {settings.SMS_APPCODE}",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(SMS_API_URL, headers=headers, params=params)

    if resp.status_code != 200:
        raise ValueError("短信发送失败，请稍后重试")

    data = resp.json()
    if data.get("code") != "0" and data.get("code") != 0:
        raise ValueError(data.get("msg", "短信发送失败"))

    # 存入 Redis（5分钟过期）
    await r.set(_redis_key(phone), code, ex=CODE_EXPIRE_SECONDS)
    # 设置冷却（60秒）
    await r.set(_cooldown_key(phone), "1", ex=COOLDOWN_SECONDS)


async def verify_sms_code(phone: str, code: str) -> bool:
    """验证短信验证码，成功后自动删除（单次可用）"""
    r = await get_redis()
    stored = await r.get(_redis_key(phone))
    if stored is None:
        return False
    if stored != code:
        return False
    # 验证成功，删除验证码（单次可用）
    await r.delete(_redis_key(phone))
    return True
