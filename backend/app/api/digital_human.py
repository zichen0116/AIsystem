"""
讯飞 AI 虚拟人（在线驱动）后端接口。

- Web SDK：前端拉取 `GET .../iflytek/web-sdk-config` 后调用 `VMS.start`（需配置 dev 代理）。
- Web API：服务端代调 `vms2d_start/stop/ping`，密钥仅存服务器。

官方文档：
- Web SDK：https://www.xfyun.cn/doc/tts/virtual_human/Web-SDK.html
- Web API：https://static.xfyun.cn/doc/tts/virtual_human/API.html
"""
import httpx
from fastapi import APIRouter, Body, HTTPException, status

from app.core.auth import CurrentUser
from app.core.config import get_settings
from app.schemas.digital_human import (
    IflytekWebSdkConfigResponse,
    Vms2dStartRequest,
    VmsSessionRequest,
)
from app.services import iflytek_vms_client

router = APIRouter(prefix="/digital-human", tags=["数字人"])


def _iflytek_settings():
    s = get_settings()
    if not (
        s.IFLYTEK_VMS_APP_ID
        and s.IFLYTEK_VMS_API_KEY
        and s.IFLYTEK_VMS_API_SECRET
    ):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="未配置讯飞虚拟人（IFLYTEK_VMS_APP_ID / API_KEY / API_SECRET）",
        )
    return s


@router.get(
    "/iflytek/web-sdk-config",
    response_model=IflytekWebSdkConfigResponse,
    response_model_by_alias=True,
    summary="Web SDK 初始化参数（需登录）",
)
async def get_iflytek_web_sdk_config(_user: CurrentUser):
    """返回数字人前端初始化参数（Avatar Platform + 旧版 VMS 字段兼容）。"""
    s = _iflytek_settings()
    scene = (s.IFLYTEK_AVATAR_SCENE_ID or s.IFLYTEK_VMS_SERVICE_ID or "").strip()
    return IflytekWebSdkConfigResponse(
        app_id=s.IFLYTEK_VMS_APP_ID,
        api_key=s.IFLYTEK_VMS_API_KEY,
        api_secret=s.IFLYTEK_VMS_API_SECRET,
        default_avatar_id=s.IFLYTEK_VMS_DEFAULT_AVATAR_ID,
        service_id=s.IFLYTEK_VMS_SERVICE_ID or None,
        scene_id=scene or None,
        avatar_server_url=s.IFLYTEK_AVATAR_SERVER_URL,
        vms_host=s.IFLYTEK_VMS_HOST,
        default_width=s.IFLYTEK_VMS_DEFAULT_WIDTH,
        default_height=s.IFLYTEK_VMS_DEFAULT_HEIGHT,
        stream_protocol=s.IFLYTEK_VMS_STREAM_PROTOCOL,
        default_tts_vcn=s.IFLYTEK_AVATAR_TTS_VCN or "x4_xiaoxuan",
    )


@router.post(
    "/iflytek/vms2d/start",
    summary="服务端代调：启动会话（Web API）",
)
async def post_vms2d_start(
    _user: CurrentUser,
    body: Vms2dStartRequest = Body(default_factory=Vms2dStartRequest),
):
    """使用 HMAC 鉴权调用讯飞 `vms2d_start`，密钥不经过浏览器。"""
    s = _iflytek_settings()
    b = body
    try:
        return await iflytek_vms_client.vms2d_start(
            s,
            avatar_id=b.avatar_id,
            width=b.width,
            height=b.height,
            protocol=b.protocol,
            uid=b.uid,
        )
    except httpx.HTTPStatusError as e:
        detail = e.response.text[:800] if e.response is not None else str(e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"讯飞 VMS 请求失败: {detail}",
        ) from e
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"连接讯飞 VMS 失败: {e!s}",
        ) from e


@router.post("/iflytek/vms2d/stop", summary="服务端代调：停止会话")
async def post_vms2d_stop(_user: CurrentUser, body: VmsSessionRequest):
    s = _iflytek_settings()
    try:
        return await iflytek_vms_client.vms2d_stop(
            s, session=body.session, uid=body.uid
        )
    except httpx.HTTPStatusError as e:
        detail = e.response.text[:800] if e.response is not None else str(e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"讯飞 VMS 请求失败: {detail}",
        ) from e
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"连接讯飞 VMS 失败: {e!s}",
        ) from e


@router.post("/iflytek/vms2d/ping", summary="服务端代调：会话心跳")
async def post_vms2d_ping(_user: CurrentUser, body: VmsSessionRequest):
    s = _iflytek_settings()
    try:
        return await iflytek_vms_client.vms2d_ping(
            s, session=body.session, uid=body.uid
        )
    except httpx.HTTPStatusError as e:
        detail = e.response.text[:800] if e.response is not None else str(e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"讯飞 VMS 请求失败: {detail}",
        ) from e
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"连接讯飞 VMS 失败: {e!s}",
        ) from e
