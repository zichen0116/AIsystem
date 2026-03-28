"""
认证相关 Schema
"""
from pydantic import BaseModel, Field
from datetime import datetime


class UserRegister(BaseModel):
    """用户注册请求"""
    phone: str = Field(..., min_length=11, max_length=20)
    password: str = Field(..., min_length=6)
    full_name: str | None = None
    code: str = Field(..., min_length=4, max_length=8, description="短信验证码")


class UserLogin(BaseModel):
    """用户登录请求"""
    phone: str = Field(..., min_length=11, max_length=20)
    password: str = Field(...)


class UserResponse(BaseModel):
    """用户信息响应"""
    id: int
    phone: str
    full_name: str | None
    is_admin: bool
    email: str | None = None
    subject: str | None = None
    school: str | None = None
    employee_id: str | None = None
    bio: str | None = None
    two_fa_enabled: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}


class LoginResponse(BaseModel):
    """登录/注册响应（token + 用户信息）"""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class TokenResponse(BaseModel):
    """令牌响应（保留兼容）"""
    access_token: str
    token_type: str = "bearer"


class ChangePassword(BaseModel):
    """修改密码请求"""
    old_password: str = Field(..., min_length=6)
    new_password: str = Field(..., min_length=6)


class SendCodeRequest(BaseModel):
    """发送短信验证码请求"""
    phone: str = Field(..., min_length=11, max_length=20)


class UpdateProfile(BaseModel):
    """更新个人资料请求"""
    full_name: str | None = Field(None, max_length=100)
    subject: str | None = Field(None, max_length=100)
    school: str | None = Field(None, max_length=200)
    employee_id: str | None = Field(None, max_length=50)
    bio: str | None = Field(None, max_length=1000)


class ChangePhone(BaseModel):
    """修改手机号请求"""
    new_phone: str = Field(..., min_length=11, max_length=20)
    code: str = Field(..., min_length=4, max_length=8, description="短信验证码")


class ChangeEmail(BaseModel):
    """修改邮箱请求"""
    new_email: str = Field(..., max_length=255)


class Toggle2FA(BaseModel):
    """开启/关闭 2FA 请求"""
    enable: bool
    code: str | None = Field(None, min_length=6, max_length=6, description="邮箱验证码（开启时必填）")


class TwoFARequired(BaseModel):
    """登录返回：需要 2FA 二次验证"""
    requires_2fa: bool = True
    temp_token: str
    masked_email: str


class Login2FAVerify(BaseModel):
    """2FA 登录验证请求"""
    temp_token: str
    code: str = Field(..., min_length=6, max_length=6)


class SendEmailCodeRequest(BaseModel):
    """发送邮箱验证码请求（使用当前登录用户绑定的邮箱）"""
    pass
