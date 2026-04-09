# 课堂预演 MVP 设计文档（第一阶段）

## 1. 项目定位

从 OpenMAIC 项目中提取"讲解模式 + 聚焦/高亮 + 翻页 + 语音"核心能力，重构为教师端可用的"课堂预演 / 教学模拟"模块，集成到现有 Vue 3 + FastAPI 系统中。

**不是**简单复制 OpenMAIC，而是：
- 只保留教师端场景，不开放学生端
- 以"课堂预演"名义呈现，非"学习助手"
- 遵循现有系统的架构模式（Pinia、FastAPI 路由、SQLAlchemy ORM）

## 2. 第一阶段范围

### 做什么
- 定义预演数据模型与动作协议
- 设计预演会话表与状态流转
- 完成后端 SSE 流式生成接口
- 完成 Vue 播放页 MVP（PPTist 只读渲染 + Spotlight/Laser 遮罩）
- 完成独立的"新建预演"入口页面
- 补齐会话保存、历史查看、恢复播放

### 不做什么
- 不做白板、圆桌/讨论
- 不做学生端
- 不做用户上传 PPT 及解析
- 不做 PPT 生成完成后的跳转入口（第二阶段）
- 不做"我的课程"中的预演入口（第二阶段）

## 3. 技术决策

| 决策项 | 选择 | 理由 |
|--------|------|------|
| PPT 渲染 | PPTist Vue 版（只读模式） | PPTist 原生 Vue 3，支持元素级 ID 适配聚焦 |
| 生成流程 | SSE 流式生成 + 即时播放 | 体验更流畅，第一页就绪即可播放 |
| SSE 实现 | FastAPI StreamingResponse | 与现有教案生成一致，简单直接 |
| 动作协议 | speech + spotlight + laser + navigate | MVP 核心子集 |
| TTS | DashScope TTS，第一阶段接入 | 现有系统已有集成 |
| 数据持久化 | 后端 PostgreSQL | 多租户按 user_id 隔离，跨设备访问 |
| 预演入口 | 仅独立的"新建预演"页面 | 其他入口第二阶段再接 |

## 4. 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    前端 (Vue 3 + Pinia)                          │
├────────────────┬──────────────────┬─────────────────────────────┤
│ RehearsalNew   │ RehearsalPlay    │ RehearsalHistory            │
│ 主题输入       │ PPTist Renderer  │ 会话列表                    │
│ 生成进度       │ Spotlight Overlay│ 状态标签                    │
│                │ 字幕面板         │ 播放/恢复                   │
│                │ 播放控制栏       │                             │
├────────────────┴──────────────────┴─────────────────────────────┤
│              Pinia Store: useRehearsalStore                      │
│  session, scenes[], currentSceneIndex, playbackState,            │
│  actionIndex, spotlightTarget, laserTarget, audioPlayer          │
├─────────────────────────────────────────────────────────────────┤
│              PlaybackEngine (前端 JS 状态机)                     │
│  idle → playing → paused                                        │
│  processNext(): speech→等音频完 | spotlight/laser→即发即忘       │
└──────────────────────────┬──────────────────────────────────────┘
                           │ SSE / REST
┌──────────────────────────┴──────────────────────────────────────┐
│                    后端 (FastAPI)                                │
│  /api/v1/rehearsal/                                              │
│  ├── POST /generate-stream   SSE 流式生成                       │
│  ├── GET  /sessions          会话列表                           │
│  ├── GET  /sessions/{id}     获取完整预演数据                   │
│  ├── PATCH /sessions/{id}    更新播放进度                       │
│  └── DELETE /sessions/{id}   删除预演                           │
├─────────────────────────────────────────────────────────────────┤
│  Services:                                                       │
│  ├── RehearsalGenerationService (LLM 编排 + SSE)                │
│  ├── RehearsalSessionService    (CRUD + 状态)                   │
│  └── TTSService                 (DashScope 语音合成)            │
├─────────────────────────────────────────────────────────────────┤
│  Models (PostgreSQL):                                            │
│  ├── rehearsal_sessions                                          │
│  └── rehearsal_scenes                                            │
└─────────────────────────────────────────────────────────────────┘
```

## 5. 数据模型

### 5.1 rehearsal_sessions

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | 自增主键 |
| user_id | Integer FK → users.id | 所属用户 |
| title | String(200) | 预演标题（LLM 生成或用户输入） |
| topic | Text | 用户输入的原始主题 |
| status | Enum | generating / ready / failed |
| total_scenes | Integer | 总场景数（大纲生成后填入） |
| ready_scenes | Integer | 已就绪场景数（逐步递增） |
| playback_snapshot | JSONB | `{sceneIndex, actionIndex}` |
| language | String(10) | zh-CN / en-US |
| settings | JSONB | `{voice, speed, enableTTS}` |
| error_message | Text | 失败时的错误信息 |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

### 5.2 rehearsal_scenes

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | 自增主键 |
| session_id | Integer FK → rehearsal_sessions.id | 所属会话 |
| scene_order | Integer | 场景顺序（从 0 开始） |
| title | String(200) | 场景标题 |
| slide_content | JSONB | PPTist Slide JSON（完整幻灯片数据） |
| actions | JSONB | Action[] 动作序列 |
| key_points | JSONB | 本页要点列表 |
| created_at | DateTime | 创建时间 |

## 6. 动作协议

### 6.1 动作类型

| 类型 | 执行模式 | 说明 |
|------|----------|------|
| speech | 同步（等音频/计时结束） | 讲解文本 + 可选 TTS 音频 |
| spotlight | 即发即忘 | 聚焦元素，其余变暗 |
| laser | 即发即忘 | 激光笔指向元素 |
| navigate | 即发即忘 | 切换到目标场景 |

### 6.2 动作数据结构

```typescript
// SpeechAction
{
  type: "speech",
  text: string,        // 讲稿文本（必填）
  audioUrl: string?,   // TTS 音频地址（可选，无则用阅读计时器）
  duration: number     // 预估时长 ms（无音频时用于自动计时）
}

// SpotlightAction
{
  type: "spotlight",
  elementId: string,   // PPTist 元素 ID
  dimOpacity: number   // 0-1，默认 0.4
}

// LaserAction
{
  type: "laser",
  elementId: string,   // 指向的元素 ID
  color: string        // 激光颜色，默认 "#ff0000"
}

// NavigateAction
{
  type: "navigate",
  targetSceneIndex: number  // 目标场景序号
}
```

### 6.3 执行规则

- **即发即忘动作**（spotlight, laser, navigate）：执行后立即调用 processNext()
- **同步动作**（speech）：等音频播放完毕或计时结束后调用 processNext()
- spotlight 和 laser 在下一个 speech 或 navigate 动作开始前自动清除
- 典型序列：`spotlight → speech → laser → speech → navigate → spotlight → speech ...`

## 7. SSE 生成流程

### 7.1 两阶段管线

```
POST /api/v1/rehearsal/generate-stream
Content-Type: text/event-stream

Stage 1: LLM 生成场景大纲（SceneOutline[]）
  → event: session_created  data: {sessionId, title}
  → event: outline_ready    data: {outlines: [{title, keyPoints, description}...]}

Stage 2: 逐个场景串行生成
  对每个 outline:
    2a. LLM → PPTist Slide JSON
    2b. LLM → Action[] 动作序列
    2c. DashScope TTS → 为每个 speech action 生成音频
    → event: scene_ready  data: {sceneIndex, scene: {title, slideContent, actions}}

  → event: complete  data: {sessionId}

错误:
  → event: error  data: {message}
```

### 7.2 生成请求体

```json
{
  "topic": "高中物理 - 牛顿第二定律",
  "language": "zh-CN",
  "enableTTS": true,
  "voice": "default",
  "speed": 1.0
}
```

### 7.3 即时播放

前端收到第一个 `scene_ready` 事件后即可进入播放状态，后续场景在后台继续生成。PlaybackEngine 在播放到尚未就绪的场景时自动等待，收到该场景的 `scene_ready` 后继续。

## 8. 前端设计

### 8.1 路由

```
/rehearsal/new       → RehearsalNew.vue      新建预演
/rehearsal/play/:id  → RehearsalPlay.vue     播放页
/rehearsal/history   → RehearsalHistory.vue  历史列表
```

### 8.2 页面说明

**RehearsalNew（新建预演）**
- 主题输入框 + 语言选择 + TTS 开关
- 点击"开始生成"后建立 SSE 连接
- 显示生成进度（正在生成大纲 / 正在生成第 X/Y 页）
- 第一页就绪后自动跳转到播放页（或显示"开始播放"按钮）

**RehearsalPlay（播放页，核心）**
- 顶部：返回按钮 + 标题 + 页码指示
- 中央：PPTist SlideRenderer（只读模式）+ Spotlight/Laser 遮罩层
- 下方：讲稿字幕面板（当前 speech.text）
- 底部：播放控制栏（上一页/暂停/播放/下一页/速度/音量）
- Spotlight 效果：目标元素保持明亮，其余区域叠加半透明黑色遮罩
- Laser 效果：目标元素边缘显示红色脉冲光效

**RehearsalHistory（历史列表）**
- 卡片列表展示所有预演会话
- 显示：标题、页数、状态标签（生成中/已完成/失败）、时间
- 点击"播放"跳转到 RehearsalPlay
- 支持删除操作

### 8.3 Pinia Store: useRehearsalStore

```javascript
state: {
  // 当前会话
  currentSession: null,     // RehearsalSession
  scenes: [],               // RehearsalScene[]
  
  // 播放状态
  currentSceneIndex: 0,
  currentActionIndex: 0,
  playbackState: 'idle',    // idle | playing | paused
  
  // 视觉效果
  spotlightTarget: null,    // {elementId, dimOpacity}
  laserTarget: null,        // {elementId, color}
  
  // 生成状态
  generatingStatus: null,   // null | generating | complete | error
  
  // 历史列表
  sessions: [],
  sessionsLoading: false,
}
```

### 8.4 PlaybackEngine

前端 JS 状态机，参考 OpenMAIC 的 PlaybackEngine 实现：

```
状态: idle ──start()──→ playing ──pause()──→ paused
                ↑                              │
                └────────resume()──────────────┘

processNext():
  1. 获取当前 action = scenes[sceneIndex].actions[actionIndex]
  2. 如果 action 为空（当前场景播完）:
     - sceneIndex++，actionIndex = 0
     - 如果所有场景播完 → idle + onComplete()
     - 如果下一场景未就绪 → 等待 scene_ready 事件
  3. actionIndex++
  4. 执行 action:
     - speech: 播放音频（有 audioUrl）或启动阅读计时器 → onEnd → processNext()
     - spotlight: 设置 store.spotlightTarget → 立即 processNext()
     - laser: 设置 store.laserTarget → 立即 processNext()
     - navigate: 设置 currentSceneIndex → 立即 processNext()
```

### 8.5 PPTist 集成

- 从 PPTist 项目引入 `SlideRenderer` 组件（只读模式）
- 输入：PPTist Slide JSON（与 OpenMAIC 使用的格式相同）
- 不需要编辑功能，禁用所有编辑交互
- 在 SlideRenderer 上方叠加 Spotlight/Laser overlay 组件
- Overlay 通过元素 ID 查找目标元素的 DOM 位置，计算遮罩区域

## 9. 后端 API 接口

### 9.1 路由注册

在 `backend/app/api/__init__.py` 中注册 `/api/v1/rehearsal` 路由。

### 9.2 接口列表

```
POST   /api/v1/rehearsal/generate-stream
  请求: {topic, language, enableTTS, voice, speed}
  响应: SSE (text/event-stream)
  认证: 需要

GET    /api/v1/rehearsal/sessions
  响应: {sessions: [{id, title, topic, status, total_scenes, ready_scenes, created_at, updated_at}]}
  认证: 需要（按 user_id 过滤）

GET    /api/v1/rehearsal/sessions/{id}
  响应: {session: {...}, scenes: [{scene_order, title, slideContent, actions}]}
  认证: 需要（校验 user_id）

PATCH  /api/v1/rehearsal/sessions/{id}
  请求: {playback_snapshot?: {sceneIndex, actionIndex}}
  响应: {success: true}
  认证: 需要

DELETE /api/v1/rehearsal/sessions/{id}
  响应: {success: true}
  认证: 需要（校验 user_id）
```

### 9.3 后端服务层

**RehearsalGenerationService**
- `generate_stream(topic, language, enable_tts, voice, speed, user_id)` → AsyncGenerator
- 内部编排：
  1. 调用 LLM 生成场景大纲（参考 OpenMAIC `outline-generator.ts` 的 prompt 模板）
  2. 创建 session 记录，yield `session_created` 事件
  3. yield `outline_ready` 事件
  4. 逐个场景：调 LLM 生成 slide content + actions，调 TTS 生成音频
  5. 每完成一个场景：写入 DB，更新 ready_scenes，yield `scene_ready` 事件
  6. 全部完成后更新 status=ready，yield `complete` 事件

**RehearsalSessionService**
- `list_sessions(user_id)` → 按 updated_at 降序
- `get_session_with_scenes(session_id, user_id)` → session + scenes
- `update_playback_snapshot(session_id, user_id, snapshot)`
- `delete_session(session_id, user_id)`

**TTSService**
- `synthesize(text, voice, speed)` → audio_url
- 使用 DashScope TTS API
- 音频文件存储到 OSS（复用现有 `oss_service.py`）

## 10. LLM Prompt 设计

### 10.1 大纲生成 Prompt

参考 OpenMAIC `lib/generation/prompts/templates/requirements-to-outlines/`，适配教师场景：

- System: "你是一位资深教师，擅长设计课堂教学流程..."
- User: "请为以下主题设计 5-8 个教学场景的大纲：{topic}"
- 输出格式：JSON 数组，每项含 title, description, keyPoints[], teachingObjective

### 10.2 Slide 内容生成 Prompt

参考 OpenMAIC `lib/generation/prompts/templates/slide-content/`：

- 输入：场景大纲 + 所有大纲（上下文）
- 输出：PPTist Slide JSON（elements[], background, theme）
- 确保每个元素有唯一 id（用于 spotlight/laser 引用）

### 10.3 动作序列生成 Prompt

参考 OpenMAIC `lib/generation/prompts/templates/`：

- 输入：场景大纲 + slide content（含元素 ID 列表）
- 输出：Action[] JSON 数组
- 约束：只使用 speech/spotlight/laser/navigate 四种类型
- spotlight/laser 的 elementId 必须引用 slide 中已有的元素 ID

## 11. 文件结构规划

### 后端新增

```
backend/app/
├── api/rehearsal.py                    # 路由
├── models/rehearsal.py                 # ORM 模型
├── schemas/rehearsal.py                # Pydantic 请求/响应模型
└── services/
    ├── rehearsal_generation_service.py  # 生成编排
    ├── rehearsal_session_service.py     # CRUD
    └── tts_service.py                  # TTS（封装 DashScope 语音合成）
```

### 前端新增

```
teacher-platform/src/
├── views/rehearsal/
│   ├── RehearsalNew.vue               # 新建预演
│   ├── RehearsalPlay.vue              # 播放页
│   └── RehearsalHistory.vue           # 历史列表
├── components/rehearsal/
│   ├── SlidePlayer.vue                # PPTist 只读渲染封装
│   ├── SpotlightOverlay.vue           # 聚焦遮罩
│   ├── LaserPointer.vue               # 激光指针效果
│   ├── SubtitlePanel.vue              # 字幕面板
│   └── PlaybackControls.vue           # 播放控制栏
├── composables/
│   └── usePlaybackEngine.js           # PlaybackEngine 状态机
├── stores/
│   └── rehearsal.js                   # Pinia store
└── api/
    └── rehearsal.js                   # API 调用封装
```

## 12. 关键实现注意点

1. **PPTist 集成**：需要从 PPTist 项目中提取 SlideRenderer 相关组件和依赖，配置为只读模式。PPTist 的元素渲染依赖 ECharts（图表）、KaTeX（公式）等，需要按需引入。

2. **Spotlight 遮罩实现**：通过元素 ID 查找 PPTist 渲染的 DOM 元素，获取其 boundingRect，在 slide 容器上叠加半透明遮罩层，对目标区域留出透明窗口。使用 CSS `box-shadow: 0 0 0 9999px rgba(0,0,0,dimOpacity)` 技巧。

3. **音频播放**：使用 HTML5 Audio API。需要处理浏览器自动播放限制（首次播放需用户交互触发）。播放/暂停需与 PlaybackEngine 状态同步。

4. **SSE 断连恢复**：如果 SSE 连接中断，前端通过 `GET /sessions/{id}` 获取已生成的场景进行播放。未生成的场景将丢失（SSE 生成是一次性的），用户可选择删除后重新生成。后端在 SSE handler 中捕获客户端断连异常，将 session 状态更新为 `ready`（已有场景可用）或 `failed`（无场景可用）。

5. **播放进度持久化**：PlaybackEngine 在每次场景切换时通过 `PATCH /sessions/{id}` 更新 playback_snapshot，支持刷新页面后恢复。

6. **阅读计时器**：无音频时，根据文本长度估算时长（中文约 150ms/字，英文约 240ms/词），最短 2 秒。可按播放速度倍率调整。
