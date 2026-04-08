"""Schemas for the iFlytek digital human APIs."""

from pydantic import BaseModel, ConfigDict, Field


class IflytekWebSdkConfigResponse(BaseModel):
    """Frontend SDK bootstrap config."""

    model_config = ConfigDict(populate_by_name=True)

    app_id: str = Field(..., serialization_alias="appId", description="Control panel APPID")
    api_key: str = Field(..., serialization_alias="apiKey")
    api_secret: str = Field(..., serialization_alias="apiSecret")
    default_avatar_id: str = Field(
        ...,
        serialization_alias="defaultAvatarId",
        description="Default avatar id for avatar.avatar_id",
    )
    service_id: str | None = Field(
        None,
        serialization_alias="serviceId",
        description="Optional legacy VMS service id",
    )
    scene_id: str | None = Field(
        None,
        serialization_alias="sceneId",
        description="Avatar Platform scene id",
    )
    avatar_server_url: str = Field(
        "wss://avatar.cn-huadong-1.xf-yun.com/v1/interact",
        serialization_alias="avatarServerUrl",
        description="Avatar websocket endpoint",
    )
    vms_host: str = Field(..., serialization_alias="vmsHost", description="Legacy VMS host")
    default_width: int = Field(1280, serialization_alias="defaultWidth")
    default_height: int = Field(720, serialization_alias="defaultHeight")
    stream_protocol: str = Field(
        "xrtc",
        serialization_alias="streamProtocol",
        description="xrtc or rtmp",
    )
    default_tts_vcn: str = Field(
        "x4_xiaoxuan",
        serialization_alias="defaultTtsVcn",
        description="Required Avatar SDK tts.vcn value",
    )
    notes: str = Field(
        "Avatar SDK uses the ESM bundle under src/libs and requires setGlobalParams.tts.vcn.",
        description="Integration notes",
    )


class Vms2dStartRequest(BaseModel):
    avatar_id: str | None = Field(None, description="Optional avatar id override")
    width: int | None = None
    height: int | None = None
    protocol: str | None = Field(None, description="xrtc or rtmp")
    uid: str = Field("", description="Optional user uid")


class VmsSessionRequest(BaseModel):
    session: str = Field(..., description="Session returned by vms2d_start")
    uid: str = ""


class AdminDigitalHumanHistoryItem(BaseModel):
    role: str = Field(..., description="user or assistant")
    content: str = Field(..., description="message content")


class AdminDigitalHumanChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="Latest admin message")
    history: list[AdminDigitalHumanHistoryItem] = Field(
        default_factory=list,
        description="Recent conversation turns from frontend memory",
    )


class AdminDigitalHumanChatResponse(BaseModel):
    answer: str = Field(..., description="Full assistant answer")
    speak_text: str = Field(..., description="Text to send to avatar writeText")
    mode: str = Field(..., description="intro or chat")
