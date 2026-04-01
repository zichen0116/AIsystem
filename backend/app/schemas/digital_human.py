"""数字人（讯飞 VMS）相关请求/响应模型。"""
from pydantic import BaseModel, ConfigDict, Field


class IflytekWebSdkConfigResponse(BaseModel):
    """
    供前端数字人 SDK 初始化。

    - Avatar Platform（`avatar-sdk-web`）：需 sceneId、serverUrl，流程为 setApiInfo → setGlobalParams → start。
    - 旧版 VMS（`VMS.start`）：仍可使用 defaultAvatarId、vmsHost 等字段作兼容。

    注意：返回 api_secret 仍会被前端持有；生产环境可优先使用服务端代调接口。
    """

    model_config = ConfigDict(populate_by_name=True)

    app_id: str = Field(..., serialization_alias="appId", description="控制台 APPID")
    api_key: str = Field(..., serialization_alias="apiKey")
    api_secret: str = Field(..., serialization_alias="apiSecret")
    default_avatar_id: str = Field(
        ...,
        serialization_alias="defaultAvatarId",
        description="默认形象 ID（Avatar 对应 avatar.avatar_id）",
    )
    service_id: str | None = Field(
        None, serialization_alias="serviceId", description="控制台接口服务 ID（可选）"
    )
    scene_id: str | None = Field(
        None,
        serialization_alias="sceneId",
        description="Avatar Platform 交互场景 ID（与控制台「接口服务」一致时可填）",
    )
    avatar_server_url: str = Field(
        "wss://avatar.cn-huadong-1.xf-yun.com/v1/interact",
        serialization_alias="avatarServerUrl",
        description="Avatar WebSocket 服务地址",
    )
    vms_host: str = Field(
        ..., serialization_alias="vmsHost", description="VMS 域名（旧版 VMS 代理用）"
    )
    default_width: int = Field(1280, serialization_alias="defaultWidth")
    default_height: int = Field(720, serialization_alias="defaultHeight")
    stream_protocol: str = Field(
        "xrtc",
        serialization_alias="streamProtocol",
        description="xrtc 或 rtmp（旧版 VMS）",
    )
    default_tts_vcn: str = Field(
        "x4_xiaoxuan",
        serialization_alias="defaultTtsVcn",
        description="Avatar SDK 全局 tts.vcn（必填，不可为空）",
    )
    notes: str = Field(
        "Avatar SDK：src/libs 下 ESM；setGlobalParams.tts.vcn 必填。",
        description="集成提示",
    )


class Vms2dStartRequest(BaseModel):
    avatar_id: str | None = Field(None, description="形象 ID，缺省用环境变量默认")
    width: int | None = None
    height: int | None = None
    protocol: str | None = Field(None, description="拉流协议：xrtc / rtmp")
    uid: str = Field("", description="用户服务 uid，可选")


class VmsSessionRequest(BaseModel):
    session: str = Field(..., description="vms2d_start 返回的 session")
    uid: str = ""
