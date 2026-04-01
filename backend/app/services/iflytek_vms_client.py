"""
讯飞 AI 虚拟人 VMS 私有 HTTP 接口客户端（异步）。

用于在后端代发请求，密钥不落浏览器（与 Web SDK 直连可二选一或组合）。

文档：https://static.xfyun.cn/doc/tts/virtual_human/API.html
"""
from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

import httpx

from app.core.config import Settings
from app.services.iflytek_vms_auth import (
    build_authorization_header_value,
    rfc1123_gmt_now,
)


def _request_line(path: str) -> str:
    if not path.startswith("/"):
        path = "/" + path
    return f"POST {path} HTTP/1.1"


def _signed_post_url(settings: Settings, path: str) -> str:
    host = settings.IFLYTEK_VMS_HOST.strip()
    date = rfc1123_gmt_now()
    auth = build_authorization_header_value(
        settings.IFLYTEK_VMS_API_KEY,
        settings.IFLYTEK_VMS_API_SECRET,
        host,
        _request_line(path),
        date,
    )
    base = f"https://{host}{path}"
    q = urlencode({"host": host, "date": date, "authorization": auth})
    return f"{base}?{q}"


async def vms2d_start(
    settings: Settings,
    *,
    avatar_id: str | None = None,
    width: int | None = None,
    height: int | None = None,
    protocol: str | None = None,
    uid: str = "",
) -> dict[str, Any]:
    path = "/v1/private/vms2d_start"
    url = _signed_post_url(settings, path)
    aid = avatar_id or settings.IFLYTEK_VMS_DEFAULT_AVATAR_ID
    w = width if width is not None else settings.IFLYTEK_VMS_DEFAULT_WIDTH
    h = height if height is not None else settings.IFLYTEK_VMS_DEFAULT_HEIGHT
    proto = (protocol or settings.IFLYTEK_VMS_STREAM_PROTOCOL).strip().lower()
    body = {
        "header": {
            "app_id": settings.IFLYTEK_VMS_APP_ID,
            "uid": uid,
        },
        "parameter": {
            "vmr": {
                "stream": {"protocol": proto},
                "avatar_id": aid,
                "width": w,
                "height": h,
            }
        },
    }
    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=15.0)) as client:
        r = await client.post(url, json=body)
    r.raise_for_status()
    return r.json()


async def vms2d_stop(
    settings: Settings,
    *,
    session: str,
    uid: str = "",
) -> dict[str, Any]:
    path = "/v1/private/vms2d_stop"
    url = _signed_post_url(settings, path)
    body = {
        "header": {
            "app_id": settings.IFLYTEK_VMS_APP_ID,
            "uid": uid,
            "session": session,
        }
    }
    async with httpx.AsyncClient(timeout=httpx.Timeout(45.0, connect=15.0)) as client:
        r = await client.post(url, json=body)
    r.raise_for_status()
    return r.json()


async def vms2d_ping(
    settings: Settings,
    *,
    session: str,
    uid: str = "",
) -> dict[str, Any]:
    path = "/v1/private/vms2d_ping"
    url = _signed_post_url(settings, path)
    body = {
        "header": {
            "app_id": settings.IFLYTEK_VMS_APP_ID,
            "uid": uid,
            "session": session,
        }
    }
    async with httpx.AsyncClient(timeout=httpx.Timeout(45.0, connect=15.0)) as client:
        r = await client.post(url, json=body)
    r.raise_for_status()
    return r.json()
