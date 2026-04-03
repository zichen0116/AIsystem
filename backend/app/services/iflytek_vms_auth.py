"""
讯飞 AI 虚拟人（VMS）HTTP 接口鉴权：HMAC-SHA256 + Base64。

与官方文档一致：
https://static.xfyun.cn/doc/tts/virtual_human/API.html#%E9%89%B4%E6%9D%83%E8%AF%B4%E6%98%8E

signature_origin:
host: {host}\ndate: {date}\nPOST {path} HTTP/1.1

authorization 明文经 Base64 后作为 URL 查询参数 authorization 传递。
"""
from __future__ import annotations

import base64
import hashlib
import hmac
from email.utils import formatdate


def build_signature_origin(host: str, date: str, request_line: str) -> str:
    return f"host: {host}\ndate: {date}\n{request_line}"


def hmac_sha256_b64(secret: str, message: str) -> str:
    digest = hmac.new(
        secret.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return base64.b64encode(digest).decode("ascii")


def build_authorization_header_value(
    api_key: str,
    api_secret: str,
    host: str,
    request_line: str,
    date_rfc1123: str,
) -> str:
    """返回 URL 查询参数 authorization 的值（已对 authorization 明文做 Base64）。"""
    sig_origin = build_signature_origin(host, date_rfc1123, request_line)
    signature = hmac_sha256_b64(api_secret, sig_origin)
    auth_plain = (
        f'api_key="{api_key}", algorithm="hmac-sha256", '
        f'headers="host date request-line", signature="{signature}"'
    )
    return base64.b64encode(auth_plain.encode("utf-8")).decode("ascii")


def rfc1123_gmt_now() -> str:
    """RFC1123 日期，GMT，与讯飞服务端时钟偏移校验（±300s）。"""
    return formatdate(timeval=None, localtime=False, usegmt=True)
