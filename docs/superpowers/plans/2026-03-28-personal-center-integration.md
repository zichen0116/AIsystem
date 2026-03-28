# Personal Center Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 完善个人中心功能，后端新增用户资料字段和相关 API，前端与后端完整对接，实现个人资料保存、修改密码、修改手机号（短信验证）、修改邮箱（直接修改）、2FA（邮箱验证码开关）。

**Architecture:** 后端扩展 User 模型（新增 email/subject/school/employee_id/bio/two_fa_enabled 字段），Alembic 迁移更新数据库，新增 PUT /profile、PUT /change-phone、PUT /change-email、POST /send-email-code、PUT /toggle-2fa 路由；前端 PersonalCenter.vue 绑定真实数据，user store 新增对应 actions，任教科目从 select 改为 input，注册默认 full_name 为 "user"。

**Tech Stack:** FastAPI, SQLAlchemy 2.0 async, Alembic, smtplib (QQ 邮箱 SMTP 587 STARTTLS), Pinia, Vue 3

---

## File Map

**后端 - 修改：**
- `backend/app/models/user.py` — 新增 6 个字段
- `backend/app/schemas/auth.py` — 扩展 UserResponse；新增 5 个 schema
- `backend/app/api/auth.py` — 修改 register；新增 5 个路由；更新 import
- `backend/app/core/config.py` — 新增 5 个 SMTP 配置字段

**后端 - 新建：**
- `backend/app/services/email.py` — SMTP 邮件 + Redis 验证码

**前端 - 修改：**
- `teacher-platform/src/stores/user.js` — 新增 5 个 actions
- `teacher-platform/src/views/PersonalCenter.vue` — 绑定真实数据，科目改 input，对接所有 API

---

### Task 1: 扩展 User 模型字段

**Files:**
- Modify: `backend/app/models/user.py`

- [ ] **Step 1: 在 User 模型中新增字段**

在 `backend/app/models/user.py` 中，找到 `token_version` 字段定义的末尾，在其后、`created_at` 字段之前插入以下内容：

```python
    email: Mapped[str | None] = mapped_column(
        String(255), nullable=True, unique=True, index=True
    )
    subject: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="任教科目"
    )
    school: Mapped[str | None] = mapped_column(
        String(200), nullable=True, comment="学校名称"
    )
    employee_id: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="工号"
    )
    bio: Mapped[str | None] = mapped_column(
        String(1000), nullable=True, comment="专业简介"
    )
    two_fa_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, comment="是否启用2FA邮箱验证"
    )
```

- [ ] **Step 2: 提交**

```bash
cd /d/Develop/Project/AIsystem
git add backend/app/models/user.py
git commit -m "feat(user): add profile fields and two_fa_enabled to User model"
```

---

### Task 2: 创建 Alembic 迁移并应用

**Files:**
- Create: `backend/alembic/versions/20260328_add_user_profile_fields.py` (自动生成)

- [ ] **Step 1: 生成迁移**

```bash
cd /d/Develop/Project/AIsystem/backend
alembic revision --autogenerate -m "add user profile fields"
```

- [ ] **Step 2: 检查迁移文件**

打开新生成的迁移文件，确认 `upgrade()` 包含以下操作（如自动生成不完整则手动补充）：

```python
def upgrade() -> None:
    op.add_column('users', sa.Column('email', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('subject', sa.String(100), nullable=True))
    op.add_column('users', sa.Column('school', sa.String(200), nullable=True))
    op.add_column('users', sa.Column('employee_id', sa.String(50), nullable=True))
    op.add_column('users', sa.Column('bio', sa.String(1000), nullable=True))
    op.add_column('users', sa.Column('two_fa_enabled', sa.Boolean(),
                                     nullable=False, server_default='false'))
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

def downgrade() -> None:
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_column('users', 'two_fa_enabled')
    op.drop_column('users', 'bio')
    op.drop_column('users', 'employee_id')
    op.drop_column('users', 'school')
    op.drop_column('users', 'subject')
    op.drop_column('users', 'email')
```

- [ ] **Step 3: 应用迁移**

```bash
cd /d/Develop/Project/AIsystem/backend
alembic upgrade head
```

预期输出：`Running upgrade ... -> ..., add user profile fields`

- [ ] **Step 4: 提交迁移文件**

```bash
cd /d/Develop/Project/AIsystem
git add backend/alembic/
git commit -m "feat(db): add migration for user profile fields"
```

---

### Task 3: 邮件服务 + 配置

**Files:**
- Create: `backend/app/services/email.py`
- Modify: `backend/app/core/config.py`

- [ ] **Step 1: 在 config.py 的 Settings 类中，紧跟 `SMS_APPCODE` 后新增**

```python
    # ========== 邮件服务（QQ 邮箱 SMTP）==========
    EMAIL_SMTP_HOST: str = "smtp.qq.com"
    EMAIL_SMTP_PORT: int = 587
    EMAIL_SMTP_USER: str = "zzcn.leo@qq.com"
    EMAIL_SMTP_PASSWORD: str = "qhwvhhocckzrfieg"
    EMAIL_FROM_NAME: str = "AI教学平台"
```

- [ ] **Step 2: 创建 `backend/app/services/email.py`**

```python
"""
邮件发送服务（QQ 邮箱 SMTP）
- 发送 2FA 验证码邮件
- Redis 存储验证码（5分钟过期、60秒冷却）
"""
import asyncio
import random
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import redis.asyncio as aioredis

from app.core.config import settings

_redis: aioredis.Redis | None = None

CODE_LENGTH = 6
CODE_EXPIRE_SECONDS = 300
COOLDOWN_SECONDS = 60


def _email_code_key(email: str) -> str:
    return f"email:code:{email}"


def _email_cooldown_key(email: str) -> str:
    return f"email:cooldown:{email}"


async def _get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis


def _generate_code() -> str:
    return "".join([str(random.randint(0, 9)) for _ in range(CODE_LENGTH)])


def _send_smtp_sync(to_email: str, code: str) -> None:
    msg = MIMEMultipart()
    msg["From"] = f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_SMTP_USER}>"
    msg["To"] = to_email
    msg["Subject"] = "AI教学平台 - 邮箱验证码"
    body = f"""
    <div style="font-family:sans-serif;max-width:480px;margin:0 auto">
      <h2 style="color:#3b82f6">AI 教学平台</h2>
      <p>您的验证码为：</p>
      <div style="font-size:2rem;font-weight:bold;letter-spacing:8px;
                  color:#1e293b;padding:16px 0">{code}</div>
      <p style="color:#64748b">验证码 5 分钟内有效，请勿泄露给他人。</p>
    </div>
    """
    msg.attach(MIMEText(body, "html", "utf-8"))
    context = ssl.create_default_context()
    with smtplib.SMTP(settings.EMAIL_SMTP_HOST, settings.EMAIL_SMTP_PORT) as smtp:
        smtp.ehlo()
        smtp.starttls(context=context)
        smtp.login(settings.EMAIL_SMTP_USER, settings.EMAIL_SMTP_PASSWORD)
        smtp.sendmail(settings.EMAIL_SMTP_USER, to_email, msg.as_string())


async def send_email_code(email: str) -> None:
    """发送邮箱验证码。Raises ValueError on cooldown or send failure."""
    r = await _get_redis()
    if await r.exists(_email_cooldown_key(email)):
        ttl = await r.ttl(_email_cooldown_key(email))
        raise ValueError(f"发送太频繁，请 {ttl} 秒后重试")
    code = _generate_code()
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _send_smtp_sync, email, code)
    except Exception as e:
        raise ValueError(f"邮件发送失败：{e}")
    await r.set(_email_code_key(email), code, ex=CODE_EXPIRE_SECONDS)
    await r.set(_email_cooldown_key(email), "1", ex=COOLDOWN_SECONDS)


async def verify_email_code(email: str, code: str) -> bool:
    """验证邮箱验证码，成功后自动删除（单次可用）"""
    r = await _get_redis()
    stored = await r.get(_email_code_key(email))
    if stored is None or stored != code:
        return False
    await r.delete(_email_code_key(email))
    return True
```

- [ ] **Step 3: 提交**

```bash
cd /d/Develop/Project/AIsystem
git add backend/app/services/email.py backend/app/core/config.py
git commit -m "feat(email): add QQ SMTP email service for 2FA codes"
```

---

### Task 4: 更新 Pydantic Schemas

**Files:**
- Modify: `backend/app/schemas/auth.py`

- [ ] **Step 1: 完整替换 `backend/app/schemas/auth.py`**

```python
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
    email: str | None
    subject: str | None
    school: str | None
    employee_id: str | None
    bio: str | None
    two_fa_enabled: bool
    is_admin: bool
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
    """更新用户资料请求"""
    full_name: str | None = Field(None, max_length=100)
    subject: str | None = Field(None, max_length=100)
    school: str | None = Field(None, max_length=200)
    employee_id: str | None = Field(None, max_length=50)
    bio: str | None = Field(None, max_length=1000)


class ChangePhone(BaseModel):
    """修改手机号请求（短信验证码验证）"""
    new_phone: str = Field(..., min_length=11, max_length=20)
    code: str = Field(..., min_length=4, max_length=8, description="新手机号收到的短信验证码")


class ChangeEmail(BaseModel):
    """修改邮箱请求（直接修改）"""
    new_email: str = Field(..., max_length=255)


class SendEmailCodeRequest(BaseModel):
    """发送邮箱验证码请求（2FA 开启时使用）"""
    email: str = Field(..., max_length=255)


class Toggle2FA(BaseModel):
    """开启/关闭 2FA 请求"""
    enable: bool
```

- [ ] **Step 2: 提交**

```bash
cd /d/Develop/Project/AIsystem
git add backend/app/schemas/auth.py
git commit -m "feat(schema): add profile/2fa/phone/email schemas, expand UserResponse"
```

---

### Task 5: 新增后端 API 路由

**Files:**
- Modify: `backend/app/api/auth.py`

- [ ] **Step 1: 修改 register，默认 full_name 为 "user"**

在 `backend/app/api/auth.py` 中找到：

```python
    user = User(
        phone=data.phone,
        password_hash=hash_password(data.password),
        full_name=data.full_name
    )
```

替换为：

```python
    user = User(
        phone=data.phone,
        password_hash=hash_password(data.password),
        full_name=data.full_name or "user"
    )
```

- [ ] **Step 2: 更新 imports（在文件顶部）**

找到原有：
```python
from app.schemas.auth import (
    UserRegister, UserLogin, LoginResponse, UserResponse,
    ChangePassword, SendCodeRequest,
)
from app.services.sms import send_sms_code, verify_sms_code
```

替换为：

```python
from app.schemas.auth import (
    UserRegister, UserLogin, LoginResponse, UserResponse,
    ChangePassword, SendCodeRequest,
    UpdateProfile, ChangePhone, ChangeEmail, SendEmailCodeRequest, Toggle2FA,
)
from app.services.sms import send_sms_code, verify_sms_code
from app.services.email import send_email_code, verify_email_code
```

- [ ] **Step 3: 在 auth.py 末尾追加 5 个新路由**

在文件 `get_me` 路由之后追加：

```python
@router.put("/profile", response_model=UserResponse)
async def update_profile(
    data: UpdateProfile,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """更新用户资料（姓名、科目、学校、工号、简介）"""
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(current_user, field, value)
    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.put("/change-phone", status_code=status.HTTP_200_OK)
async def change_phone(
    data: ChangePhone,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """修改手机号（需短信验证码验证新手机号）"""
    # 检查新手机号是否已被占用
    result = await db.execute(select(User).where(User.phone == data.new_phone))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该手机号已被注册"
        )
    # 验证新手机号收到的短信验证码
    if not await verify_sms_code(data.new_phone, data.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="验证码错误或已过期"
        )
    current_user.phone = data.new_phone
    await db.commit()
    return {"message": "手机号修改成功"}


@router.put("/change-email", status_code=status.HTTP_200_OK)
async def change_email(
    data: ChangeEmail,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """修改邮箱（直接修改，无需验证码）"""
    # 检查邮箱是否已被占用
    result = await db.execute(select(User).where(User.email == data.new_email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该邮箱已被绑定"
        )
    current_user.email = data.new_email
    await db.commit()
    return {"message": "邮箱修改成功"}


@router.post("/send-email-code", status_code=status.HTTP_200_OK)
async def send_email_code_endpoint(
    data: SendEmailCodeRequest,
    current_user: CurrentUser
):
    """发送邮箱验证码（用于开启 2FA）"""
    try:
        await send_email_code(data.email)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(e)
        )
    return {"message": "验证码已发送"}


@router.put("/toggle-2fa", response_model=UserResponse)
async def toggle_2fa(
    data: Toggle2FA,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """开启或关闭 2FA。开启时需先调用 /send-email-code 获取验证码并提供绑定邮箱。"""
    if data.enable:
        # 开启 2FA：需要验证邮箱验证码
        if not current_user.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="请先绑定邮箱"
            )
        if not data.code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="开启 2FA 需要提供邮箱验证码"
            )
        if not await verify_email_code(current_user.email, data.code):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="验证码错误或已过期"
            )
    current_user.two_fa_enabled = data.enable
    await db.commit()
    await db.refresh(current_user)
    return current_user
```

- [ ] **Step 4: 提交**

```bash
cd /d/Develop/Project/AIsystem
git add backend/app/api/auth.py
git commit -m "feat(api): add profile/phone/email/2fa endpoints, default full_name to user"
```

---

### Task 6: 更新前端 user store

**Files:**
- Modify: `teacher-platform/src/stores/user.js`

- [ ] **Step 1: 完整替换 `teacher-platform/src/stores/user.js`**

```js
import { defineStore } from 'pinia'
import { apiRequest, setToken, removeToken, getToken } from '../api/http'

export const useUserStore = defineStore('user', {
  state: () => ({
    isLoggedIn: false,
    userInfo: null,
  }),

  actions: {
    async login(phone, password) {
      const data = await apiRequest('/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone, password }),
      })
      setToken(data.access_token)
      this.isLoggedIn = true
      this.userInfo = data.user
      return data.user
    },

    async register(phone, password, code, fullName) {
      const body = { phone, password, code }
      if (fullName) body.full_name = fullName
      const data = await apiRequest('/api/v1/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      setToken(data.access_token)
      this.isLoggedIn = true
      this.userInfo = data.user
      return data.user
    },

    async logout() {
      const token = getToken()
      this.isLoggedIn = false
      this.userInfo = null
      if (token) {
        try {
          const API_BASE = (import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000').replace(/\/$/, '')
          await fetch(`${API_BASE}/api/v1/auth/logout`, {
            method: 'POST',
            headers: { Authorization: `Bearer ${token}` },
          })
        } catch {
          // 忽略网络错误
        }
      }
      removeToken()
    },

    async fetchUser() {
      const token = getToken()
      if (!token) return false
      try {
        const user = await apiRequest('/api/v1/auth/me')
        this.isLoggedIn = true
        this.userInfo = user
        return true
      } catch {
        removeToken()
        this.isLoggedIn = false
        this.userInfo = null
        return false
      }
    },

    async updateProfile(profileData) {
      // profileData: { full_name, subject, school, employee_id, bio }
      const user = await apiRequest('/api/v1/auth/profile', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(profileData),
      })
      this.userInfo = user
      return user
    },

    async changePassword(oldPassword, newPassword) {
      await apiRequest('/api/v1/auth/change-password', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ old_password: oldPassword, new_password: newPassword }),
      })
    },

    async changePhone(newPhone, code) {
      await apiRequest('/api/v1/auth/change-phone', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ new_phone: newPhone, code }),
      })
      if (this.userInfo) this.userInfo.phone = newPhone
    },

    async changeEmail(newEmail) {
      await apiRequest('/api/v1/auth/change-email', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ new_email: newEmail }),
      })
      if (this.userInfo) this.userInfo.email = newEmail
    },

    async sendEmailCode(email) {
      await apiRequest('/api/v1/auth/send-email-code', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      })
    },

    async toggle2FA(enable, code) {
      const body = { enable }
      if (code) body.code = code
      const user = await apiRequest('/api/v1/auth/toggle-2fa', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      this.userInfo = user
      return user
    },
  },
})
```

- [ ] **Step 2: 提交**

```bash
cd /d/Develop/Project/AIsystem
git add teacher-platform/src/stores/user.js
git commit -m "feat(store): add profile/phone/email/2fa actions to user store"
```

---

### Task 7: 更新 PersonalCenter.vue

**Files:**
- Modify: `teacher-platform/src/views/PersonalCenter.vue`

说明：这是最大的改动。需要在 `<script setup>` 中绑定真实数据并添加表单逻辑，在 `<template>` 中替换硬编码值，将科目 `<select>` 改为 `<input>`。

- [ ] **Step 1: 在 `<script setup>` 的顶部 ref 声明之后，添加资料表单 state**

在 `const showLogoutConfirm = ref(false)` 之后添加：

```js
// 个人资料表单
const profileForm = ref({
  full_name: '',
  subject: '',
  school: '',
  employee_id: '',
  bio: '',
})
const profileSaving = ref(false)
const profileMsg = ref('')

// 初始化表单数据
function initProfileForm() {
  const u = userStore.userInfo
  if (!u) return
  profileForm.value = {
    full_name: u.full_name || '',
    subject: u.subject || '',
    school: u.school || '',
    employee_id: u.employee_id || '',
    bio: u.bio || '',
  }
}
initProfileForm()
watch(() => userStore.userInfo, initProfileForm)

async function saveProfile() {
  profileSaving.value = true
  profileMsg.value = ''
  try {
    await userStore.updateProfile(profileForm.value)
    profileMsg.value = '保存成功'
  } catch (e) {
    profileMsg.value = e.message || '保存失败'
  } finally {
    profileSaving.value = false
  }
}

function cancelProfile() {
  initProfileForm()
  profileMsg.value = ''
}
```

- [ ] **Step 2: 添加修改密码逻辑**

找到 `function openPasswordModal()` 之后，找到 `function open2FAModal()` 之前，添加：

```js
const passwordSaving = ref(false)
const passwordMsg = ref('')

async function submitPasswordChange() {
  if (newPassword.value !== confirmPassword.value) {
    passwordMsg.value = '两次密码不一致'
    return
  }
  passwordSaving.value = true
  passwordMsg.value = ''
  try {
    await userStore.changePassword(currentPassword.value, newPassword.value)
    passwordMsg.value = '密码修改成功，请重新登录'
    setTimeout(() => {
      showPasswordModal.value = false
      userStore.logout()
      router.push('/')
    }, 1500)
  } catch (e) {
    passwordMsg.value = e.message || '修改失败'
  } finally {
    passwordSaving.value = false
  }
}
```

- [ ] **Step 3: 添加修改手机号/邮箱/2FA 逻辑**

在 `submitPasswordChange` 之后添加：

```js
// 修改手机号
const showPhoneModal = ref(false)
const newPhone = ref('')
const phoneCode = ref('')
const phoneSaving = ref(false)
const phoneMsg = ref('')
const phoneSendCooldown = ref(0)
let phoneTimer = null

function openPhoneModal() {
  showPhoneModal.value = true
  newPhone.value = ''
  phoneCode.value = ''
  phoneMsg.value = ''
}

async function sendPhoneCode() {
  if (!newPhone.value || newPhone.value.length < 11) {
    phoneMsg.value = '请输入正确的手机号'
    return
  }
  try {
    await import('../api/http').then(({ apiRequest }) =>
      apiRequest('/api/v1/auth/send-code', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone: newPhone.value }),
      })
    )
    phoneMsg.value = '验证码已发送'
    phoneSendCooldown.value = 60
    phoneTimer = setInterval(() => {
      phoneSendCooldown.value--
      if (phoneSendCooldown.value <= 0) clearInterval(phoneTimer)
    }, 1000)
  } catch (e) {
    phoneMsg.value = e.message || '发送失败'
  }
}

async function submitPhoneChange() {
  phoneSaving.value = true
  phoneMsg.value = ''
  try {
    await userStore.changePhone(newPhone.value, phoneCode.value)
    phoneMsg.value = '手机号修改成功'
    setTimeout(() => { showPhoneModal.value = false }, 1200)
  } catch (e) {
    phoneMsg.value = e.message || '修改失败'
  } finally {
    phoneSaving.value = false
  }
}

// 修改邮箱
const showEmailModal = ref(false)
const newEmail = ref('')
const emailSaving = ref(false)
const emailMsg = ref('')

function openEmailModal() {
  showEmailModal.value = true
  newEmail.value = userStore.userInfo?.email || ''
  emailMsg.value = ''
}

async function submitEmailChange() {
  emailSaving.value = true
  emailMsg.value = ''
  try {
    await userStore.changeEmail(newEmail.value)
    emailMsg.value = '邮箱修改成功'
    setTimeout(() => { showEmailModal.value = false }, 1200)
  } catch (e) {
    emailMsg.value = e.message || '修改失败'
  } finally {
    emailSaving.value = false
  }
}

// 2FA
const twoFASaving = ref(false)
const twoFAMsg = ref('')
const show2FAEmail = ref('')
const show2FAStep = ref('send') // 'send' | 'verify'

function open2FAModal() {
  show2FAModal.value = true
  twoFACode.value = ['', '', '', '', '', '']
  twoFAMsg.value = ''
  show2FAEmail.value = userStore.userInfo?.email || ''
  show2FAStep.value = 'send'
  resendCountdown.value = 0
}

async function send2FACode() {
  if (!show2FAEmail.value) {
    twoFAMsg.value = '请先绑定邮箱'
    return
  }
  try {
    await userStore.sendEmailCode(show2FAEmail.value)
    show2FAStep.value = 'verify'
    twoFAMsg.value = '验证码已发送到邮箱'
    resendCountdown.value = 60
    const t = setInterval(() => {
      resendCountdown.value--
      if (resendCountdown.value <= 0) clearInterval(t)
    }, 1000)
  } catch (e) {
    twoFAMsg.value = e.message || '发送失败'
  }
}

async function submit2FA() {
  const code = twoFACode.value.join('')
  if (code.length !== 6) {
    twoFAMsg.value = '请输入完整验证码'
    return
  }
  twoFASaving.value = true
  twoFAMsg.value = ''
  try {
    await userStore.toggle2FA(true, code)
    twoFAMsg.value = '2FA 已开启'
    setTimeout(() => { show2FAModal.value = false }, 1200)
  } catch (e) {
    twoFAMsg.value = e.message || '验证失败'
  } finally {
    twoFASaving.value = false
  }
}

async function disable2FA() {
  try {
    await userStore.toggle2FA(false)
  } catch (e) {
    console.error(e)
  }
}
```

- [ ] **Step 4: 替换个人信息面板中的硬编码值，绑定 profileForm**

在 `<template>` 中找到 profile 面板（`v-if="activeSideItem === 'profile'"`），将头像显示名改为真实数据，将表单字段绑定 `v-model`：

**头像显示名**（找到 `class="profile-name"` 的行，改为）：
```html
<h2 class="profile-name">{{ userStore.userInfo?.full_name || 'user' }}</h2>
```

**姓名字段**（找到 `value="陈晓明"` 或类似硬编码，改为）：
```html
<div class="form-group">
  <label>姓名</label>
  <input type="text" v-model="profileForm.full_name" />
</div>
```

**任教科目**（将 `<select>` 整体替换为 `<input>`）：
```html
<div class="form-group">
  <label>任教科目</label>
  <input type="text" v-model="profileForm.subject" placeholder="如：数学、物理" />
</div>
```

**学校名称**：
```html
<div class="form-group">
  <label>学校名称</label>
  <input type="text" v-model="profileForm.school" />
</div>
```

**邮箱**（只读展示，改为）：
```html
<div class="form-group">
  <label>邮箱</label>
  <input type="text" :value="userStore.userInfo?.email || '未绑定'" readonly class="readonly" />
</div>
```

**手机号**（只读展示）：
```html
<div class="form-group">
  <label>手机号</label>
  <input type="text" :value="userStore.userInfo?.phone || '未绑定'" readonly class="readonly" />
</div>
```

**工号**：
```html
<div class="form-group">
  <label>工号</label>
  <input type="text" v-model="profileForm.employee_id" />
</div>
```

**专业简介**：
```html
<div class="form-group full">
  <label>专业简介</label>
  <textarea rows="4" v-model="profileForm.bio"></textarea>
</div>
```

**操作按钮**（绑定 saveProfile/cancelProfile，显示状态）：
```html
<div class="action-buttons">
  <span v-if="profileMsg" style="color:#3b82f6;font-size:0.9rem">{{ profileMsg }}</span>
  <button class="cancel-btn" @click="cancelProfile">取消</button>
  <button class="save-btn" :disabled="profileSaving" @click="saveProfile">
    {{ profileSaving ? '保存中...' : '保存修改' }}
  </button>
</div>
```

- [ ] **Step 5: 更新账号安全面板**

**修改密码按钮**（已有 `@click="openPasswordModal"`，在密码 modal 中绑定提交）：

找到密码 modal 的确认按钮，改为：
```html
<button class="primary-btn" :disabled="passwordSaving" @click="submitPasswordChange">
  {{ passwordSaving ? '修改中...' : '确认修改' }}
</button>
<p v-if="passwordMsg" style="color:#ef4444;font-size:0.85rem;margin-top:8px">{{ passwordMsg }}</p>
```

**邮箱显示**（将硬编码 `j.smith@northview.edu` 替换为真实数据，并绑定更换按钮）：
```html
<div class="contact-item">
  <span class="contact-label">邮箱</span>
  <span class="contact-value">{{ userStore.userInfo?.email || '未绑定' }}</span>
  <a href="#" class="link-btn primary" @click.prevent="openEmailModal">更换</a>
</div>
```

**手机号显示**（将硬编码手机号替换为真实数据，并绑定管理按钮）：
```html
<div class="contact-item">
  <span class="contact-label">手机号</span>
  <span class="contact-value">{{ userStore.userInfo?.phone || '未绑定' }}</span>
  <a href="#" class="link-btn primary" @click.prevent="openPhoneModal">管理</a>
</div>
```

**2FA 状态显示**（根据 `userStore.userInfo?.two_fa_enabled` 动态切换）：
```html
<div class="setting-block setting-block-row">
  <div class="block-icon">🛡️</div>
  <div class="block-content">
    <h4>双重认证 (2FA)
      <span v-if="userStore.userInfo?.two_fa_enabled" class="enabled-tag">已开启</span>
      <span v-else class="disabled-tag">未开启</span>
    </h4>
    <p>通过邮箱验证码为账号增加一层安全保护。</p>
  </div>
  <button v-if="!userStore.userInfo?.two_fa_enabled" class="primary-btn" @click="open2FAModal">开启 2FA</button>
  <button v-else class="outline-btn" @click="disable2FA">关闭 2FA</button>
</div>
```

- [ ] **Step 6: 在 template 中添加三个新 modal（修改手机号、修改邮箱、2FA 开启）**

在现有的 `<!-- 修改密码 Modal -->` 和 `<!-- 2FA Modal -->` 之后的 `</Teleport>` 前，添加修改手机号和邮箱 modal（使用 `<Teleport to="body">`）：

**修改手机号 Modal：**
```html
<Teleport to="body">
  <div v-if="showPhoneModal" class="modal-overlay" @click.self="showPhoneModal = false">
    <div class="modal-box">
      <h3>修改手机号</h3>
      <p style="color:#64748b;font-size:0.9rem;margin-bottom:16px">向新手机号发送验证码完成验证</p>
      <div class="modal-form">
        <label>新手机号</label>
        <div style="display:flex;gap:8px">
          <input type="tel" v-model="newPhone" placeholder="请输入新手机号" style="flex:1" />
          <button class="outline-btn" :disabled="phoneSendCooldown > 0" @click="sendPhoneCode">
            {{ phoneSendCooldown > 0 ? `${phoneSendCooldown}s` : '发送验证码' }}
          </button>
        </div>
        <label style="margin-top:12px">验证码</label>
        <input type="text" v-model="phoneCode" placeholder="请输入验证码" maxlength="6" />
        <p v-if="phoneMsg" style="color:#3b82f6;font-size:0.85rem;margin-top:8px">{{ phoneMsg }}</p>
      </div>
      <div class="modal-actions">
        <button class="cancel-btn" @click="showPhoneModal = false">取消</button>
        <button class="primary-btn" :disabled="phoneSaving" @click="submitPhoneChange">
          {{ phoneSaving ? '修改中...' : '确认修改' }}
        </button>
      </div>
    </div>
  </div>
</Teleport>
```

**修改邮箱 Modal：**
```html
<Teleport to="body">
  <div v-if="showEmailModal" class="modal-overlay" @click.self="showEmailModal = false">
    <div class="modal-box">
      <h3>修改邮箱</h3>
      <div class="modal-form">
        <label>新邮箱地址</label>
        <input type="email" v-model="newEmail" placeholder="请输入新邮箱" />
        <p v-if="emailMsg" style="color:#3b82f6;font-size:0.85rem;margin-top:8px">{{ emailMsg }}</p>
      </div>
      <div class="modal-actions">
        <button class="cancel-btn" @click="showEmailModal = false">取消</button>
        <button class="primary-btn" :disabled="emailSaving" @click="submitEmailChange">
          {{ emailSaving ? '修改中...' : '确认修改' }}
        </button>
      </div>
    </div>
  </div>
</Teleport>
```

**2FA Modal 更新**（将原有 2FA modal 的硬编码更换为动态内容）：

找到现有的 `<!-- 2FA 开启 Modal -->` 模板块，将发送按钮和确认按钮改为：
```html
<!-- 步骤1: 发送验证码 -->
<div v-if="show2FAStep === 'send'">
  <p style="color:#64748b;font-size:0.9rem;margin-bottom:12px">
    将向 {{ show2FAEmail || '您的绑定邮箱' }} 发送验证码
  </p>
  <p v-if="twoFAMsg" style="color:#3b82f6;font-size:0.85rem">{{ twoFAMsg }}</p>
  <div class="modal-actions" style="margin-top:16px">
    <button class="cancel-btn" @click="show2FAModal = false">取消</button>
    <button class="primary-btn" @click="send2FACode">发送验证码</button>
  </div>
</div>
<!-- 步骤2: 输入验证码 -->
<div v-if="show2FAStep === 'verify'">
  <div class="code-inputs">
    <input
      v-for="(digit, i) in twoFACode"
      :key="i"
      class="code-input"
      type="text"
      maxlength="1"
      :value="digit"
      @input="handleCodeInput($event, i)"
      @keydown.backspace="handleCodeBackspace($event, i)"
    />
  </div>
  <p class="resend-text">
    <span v-if="resendCountdown > 0" class="countdown">{{ resendCountdown }}s 后可重新发送</span>
    <a v-else href="#" class="resend-link" @click.prevent="send2FACode">重新发送</a>
  </p>
  <p v-if="twoFAMsg" style="color:#3b82f6;font-size:0.85rem">{{ twoFAMsg }}</p>
  <div class="modal-actions">
    <button class="cancel-btn" @click="show2FAModal = false">取消</button>
    <button class="primary-btn" :disabled="twoFASaving" @click="submit2FA">
      {{ twoFASaving ? '验证中...' : '确认开启' }}
    </button>
  </div>
</div>
```

- [ ] **Step 7: 在 `<style>` 中补充 `.enabled-tag` 样式**

找到 `.disabled-tag` 样式，在其后面追加：

```css
.enabled-tag {
  font-size: 0.7rem;
  background: #dcfce7;
  color: #16a34a;
  padding: 2px 8px;
  border-radius: 99px;
  margin-left: 8px;
  font-weight: 500;
}
```

- [ ] **Step 8: 提交**

```bash
cd /d/Develop/Project/AIsystem
git add teacher-platform/src/views/PersonalCenter.vue
git commit -m "feat(ui): bind real data in PersonalCenter, add phone/email/2fa modals, subject to input"
```

---

### Task 8: 验证整体功能

- [ ] **Step 1: 启动后端服务**

```bash
cd /d/Develop/Project/AIsystem/backend
python run.py
```

预期：FastAPI 启动，Swagger 文档可访问 `http://127.0.0.1:8000/docs`

- [ ] **Step 2: 验证新增 API 端点存在**

访问 `http://127.0.0.1:8000/docs`，确认以下端点存在：
- `PUT /api/v1/auth/profile`
- `PUT /api/v1/auth/change-phone`
- `PUT /api/v1/auth/change-email`
- `POST /api/v1/auth/send-email-code`
- `PUT /api/v1/auth/toggle-2fa`
- `GET /api/v1/auth/me`（响应中包含 email, subject, school, employee_id, bio, two_fa_enabled）

- [ ] **Step 3: 启动前端服务**

```bash
cd /d/Develop/Project/AIsystem/teacher-platform
npm run dev
```

- [ ] **Step 4: 手动测试个人信息保存**

1. 登录账号，进入个人中心 → 个人信息
2. 修改姓名、任教科目（文本输入框）、学校、工号、简介
3. 点击「保存修改」，确认显示「保存成功」
4. 刷新页面，确认数据持久化

- [ ] **Step 5: 手动测试修改密码**

1. 进入账号安全 → 修改密码
2. 输入旧密码和新密码，点击确认
3. 确认跳转到登录页

- [ ] **Step 6: 手动测试修改手机号**

1. 点击手机号「管理」
2. 输入新手机号，发送验证码，输入验证码，确认修改

- [ ] **Step 7: 手动测试修改邮箱**

1. 点击邮箱「更换」
2. 输入新邮箱，点击确认修改
3. 确认个人信息和账号安全页邮箱已更新

- [ ] **Step 8: 手动测试 2FA 开启**

1. 确保已绑定邮箱，点击「开启 2FA」
2. 点击发送验证码，检查邮箱收到验证码
3. 输入 6 位验证码，点击「确认开启」
4. 确认 2FA 状态变为「已开启」，按钮切换为「关闭 2FA」

- [ ] **Step 9: 最终提交**

```bash
cd /d/Develop/Project/AIsystem
git add -A
git commit -m "feat(personal-center): complete profile/security center integration"
```
