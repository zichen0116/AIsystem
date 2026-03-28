# 个人中心功能完善 — 设计文档

**日期：** 2026-03-29
**分支：** feature/personal-message-manage
**状态：** 已审阅（含 ISSUES.md 修订）

---

## 1. 背景与目标

当前个人中心页面（PersonalCenter.vue）大量使用硬编码占位数据，后端 User 模型也缺少资料字段。本次目标：

1. 后端补全用户资料字段，提供 CRUD API
2. 账号安全页：修改密码（已有路由）、修改手机号（短信验证）、修改邮箱（直接修改）、2FA 开关（邮箱验证码确认开启）
3. **2FA 认证实现**：登录时若用户已开启 2FA，密码验证通过后需发送邮箱验证码并二次校验
4. 前端与后端完整对接，消除所有硬编码
5. 新注册用户默认 `full_name` 为 `"user"`
6. 任教科目从 `<select>` 改为 `<input>` 文本框
7. 登录历史表格保留现有 UI 硬编码展示，不做后端实现

---

## 2. 数据模型变更

### 2.1 User 表新增字段

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `email` | VARCHAR(255) | UNIQUE, nullable | 邮箱，可为空（未绑定） |
| `subject` | VARCHAR(100) | nullable | 任教科目 |
| `school` | VARCHAR(200) | nullable | 学校名称 |
| `employee_id` | VARCHAR(50) | nullable | 工号 |
| `bio` | VARCHAR(1000) | nullable | 专业简介 |
| `two_fa_enabled` | BOOLEAN | NOT NULL, default false | 是否启用 2FA |

通过 Alembic 迁移添加，`two_fa_enabled` 使用 `server_default='false'` 兼容已有记录。

---

## 3. API 设计

### 3.1 现有路由（修改）

| 方法 | 路径 | 变更 |
|------|------|------|
| GET | `/api/v1/auth/me` | 返回结构扩展（含新字段） |
| PUT | `/api/v1/auth/change-password` | 无变更 |
| POST | `/api/v1/auth/send-code` | 无变更 |
| POST | `/api/v1/auth/login` | **修改**：增加 2FA 流程，见下文 |

### 3.2 新增路由

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| PUT | `/api/v1/auth/profile` | 需要 | 更新资料（姓名/科目/学校/工号/简介） |
| PUT | `/api/v1/auth/change-phone` | 需要 | 修改手机号（需新手机号短信验证码） |
| PUT | `/api/v1/auth/change-email` | 需要 | 直接修改邮箱（无需验证码） |
| POST | `/api/v1/auth/send-email-code` | 需要 | 向当前用户已绑定邮箱发送验证码（2FA 开启用） |
| PUT | `/api/v1/auth/toggle-2fa` | 需要 | 开启/关闭 2FA |
| POST | `/api/v1/auth/login/2fa` | 无（使用临时 token） | 2FA 登录第二步：提交邮箱验证码 |

### 3.3 登录 2FA 流程设计

```
客户端                              服务端
  │                                    │
  │── POST /login {phone, password} ──►│
  │                                    │ 验证密码
  │                                    │ two_fa_enabled=false: 正常返回 token
  │                                    │ two_fa_enabled=true:
  │◄── 202 { requires_2fa: true,       │   生成临时 token (5min, type="2fa_pending")
  │         temp_token: "...",          │   发送验证码到 user.email
  │         masked_email: "z***@qq.com"}│
  │                                    │
  │── POST /login/2fa ────────────────►│
  │   { temp_token, code }             │ 校验 temp_token type
  │                                    │ 校验邮箱验证码
  │◄── 200 { access_token, user } ─────│ 发放正式 access_token
```

**临时 token 设计：**
- JWT payload 中增加 `type: "2fa_pending"` 字段，正式 token 不带此字段
- 过期时间 5 分钟
- `get_current_user` 依赖仍只接受不含 `type` 字段（或 type 为空）的 token，2fa_pending token 无法访问其他接口

**登录响应 Schema 变更：**
- 正常登录（无 2FA）：返回 `LoginResponse { access_token, token_type, user }`（现有结构不变）
- 需要 2FA：返回 HTTP 202 + `TwoFARequired { requires_2fa: true, temp_token, masked_email }`

### 3.4 关键安全设计决策

**send-email-code（2FA 开启用）：**
- 请求体不含 email，服务端直接使用 `current_user.email`
- 若用户未绑定邮箱则返回 400
- 防止登录用户向任意地址滥发验证码

**toggle-2fa：**
- 开启时：必须提供 6 位 code，校验 `current_user.email` 对应验证码
- 关闭时：无需验证码，直接关闭

**SMTP 凭据：**
- 不硬编码进源码，通过 `backend/.env` 注入
- `config.py` 中只写空字符串默认值，`.env` 中填写真实授权码
- 项目为私有团队仓库，.env 可提交（见 CLAUDE.md）

### 3.5 Pydantic Schema 变更

**UserResponse 扩展：** 新增 email, subject, school, employee_id, bio, two_fa_enabled 字段。

**新增 Schema：**

```
UpdateProfile       { full_name?, subject?, school?, employee_id?, bio? }
ChangePhone         { new_phone, code }          // 短信验证码
ChangeEmail         { new_email }               // 直接修改
Toggle2FA           { enable: bool, code?: str } // 开启时必须
TwoFARequired       { requires_2fa: bool, temp_token: str, masked_email: str }
Login2FAVerify      { temp_token: str, code: str }
```

`SendEmailCodeRequest`：无字段（email 取自 current_user）。

---

## 4. 邮件服务设计

- QQ 邮箱 SMTP，587 端口，STARTTLS
- 异步：`run_in_executor` 避免阻塞 event loop
- Redis 存储验证码：5 分钟过期，60 秒冷却（key: `email:code:{email}`）
- 同一邮件服务同时服务：2FA 开启验证、登录 2FA 二次验证

---

## 5. 前端设计

### 5.1 登录流程改造（LoginView.vue）

**现有流程：** `POST /login` → 成功 → 设置 token → 跳转

**新流程：**
```
POST /login
  → 200: 正常登录，设置 token，跳转
  → 202 requires_2fa=true: 展示 2FA 验证 modal
                           → 用户输入 6 位验证码
                           → POST /login/2fa {temp_token, code}
                           → 成功: 设置 token，跳转
```

2FA modal 复用现有 `code-input` 样式（6 格验证码输入框），展示 `masked_email`。

### 5.2 user store 新增 actions

| Action | 调用 API | 成功后 |
|--------|---------|--------|
| `updateProfile(data)` | PUT /profile | 更新 userInfo |
| `changePassword(old, new)` | PUT /change-password | — |
| `changePhone(phone, code)` | PUT /change-phone | 更新 userInfo.phone |
| `changeEmail(email)` | PUT /change-email | 更新 userInfo.email |
| `sendEmailCode()` | POST /send-email-code | — |
| `toggle2FA(enable, code?)` | PUT /toggle-2fa | 更新 userInfo |
| `verify2FALogin(tempToken, code)` | POST /login/2fa | 设置 token，返回 user |

### 5.3 PersonalCenter.vue 改动

**个人信息面板：**
- `profileForm` ref，`watch(userStore.userInfo)` 初始化
- 姓名/科目/学校/工号/简介绑定 `v-model`
- 任教科目：`<select>` → `<input type="text">`
- 邮箱/手机号：只读展示
- 保存/取消按钮绑定 `saveProfile()` / `cancelProfile()`

**账号安全面板：**
- 修改密码 modal：补充 `submitPasswordChange()`，成功后登出跳转
- 邮箱/手机号：展示真实值；「更换」→ `openEmailModal()`，「管理」→ `openPhoneModal()`
- 2FA：根据 `two_fa_enabled` 切换「开启/关闭」按钮，`open2FAModal()` 完整替换
- 登录历史：保留硬编码 UI 不变

**新增三个 Modal：**
1. 修改手机号：新手机号 + 短信验证码
2. 修改邮箱：新邮箱直接提交
3. 2FA 开启：Step1 发送验证码，Step2 输入 6 位确认

**2FA 关闭：** 点击「关闭 2FA」显示二次确认弹窗（"确定要关闭双重认证吗？"），用户确认后调用 `userStore.toggle2FA(false)`，无需验证码。

**2FA 默认状态：** 所有用户 `two_fa_enabled` 默认为 `false`（关闭）。

---

## 6. ISSUES.md 审阅结论

| 问题 | 采纳 | 处置方式 |
|------|------|----------|
| Toggle2FA schema 缺 code 字段 | 是 | Schema 增加 `code: str \| None`，路由强校验 |
| 2FA 模板事件名与函数不一致 | 是 | 模板统一使用 `on2FACodeInput` / `on2FACodeKeydown`（已存在于原文件）|
| SMTP 密码硬编码 | 是 | .env 注入，config.py 空字符串默认值 |
| send-email-code 可发任意邮箱 | 是 | 去掉请求体 email，改用 current_user.email |
| open2FAModal 可能重复声明 | 是 | 实现计划明确标注「完整替换旧函数」|
| 2FA 仅覆盖开关，不含登录阶段校验 | **采纳** | 新增 `/login/2fa` 路由 + 临时 token 机制 + 前端登录流程改造 |
| 步骤编排歧义 | 是 | 实现计划中明确「替换」vs「追加」|
