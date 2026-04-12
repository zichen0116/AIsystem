# 课堂预演（Lesson Rehearsal）功能 - 完整代码分析

## 📋 概述

**课堂预演** 是一个 AI 驱动的虚拟课堂演示系统，允许教师输入教学主题，系统自动生成可交互的课堂预演（包含幻灯片、讲稿、音频、动作序列）。

**技术栈：** Vue 3 + Pinia + FastAPI + SQLAlchemy + PostgreSQL

---

## 1️⃣ 前端核心文件

### 路径结构
```
teacher-platform/src/
├── views/rehearsal/
│   ├── RehearsalNew.vue          ✨ 生成界面（核心）
│   ├── RehearsalPlay.vue         ▶️ 播放界面
│   └── RehearsalLab.vue          📋 列表界面
├── components/rehearsal/
│   ├── SlideRenderer.vue         🖼️ 幻灯片渲染
│   ├── PlaybackControls.vue      🎮 播放控制
│   ├── SpotlightOverlay.vue      💡 聚焦效果
│   ├── HighlightOverlay.vue      ✏️ 高亮效果
│   └── LaserPointer.vue          🔴 激光笔
├── api/rehearsal.js              🔌 API 封装
├── stores/rehearsal.js           🗂️ Pinia 状态
└── composables/usePlaybackEngine.js  ⚙️ 播放引擎
```

### RehearsalNew.vue 核心逻辑

**3 种界面状态：**
1. **表单态** - 输入教学主题、选择语言、启用 TTS
2. **生成态** - 显示进度、场景状态、支持重试
3. **完成态** - 显示结果，可开始播放

**生成流程：**
```
表单 → SSE 连接 → 监听事件 → 轮询 DB → 更新 UI
```

**关键参数：**
```javascript
{
  topic: "高中物理 - 牛顿第二定律",
  language: "zh-CN",
  enable_tts: true,
  speed: 1.0
}
```

### API 封装 (rehearsal.js)
```javascript
generateRehearsalStream(params)         // SSE 流式生成
fetchSessions()                         // 获取会话列表
fetchSession(sessionId)                 // 获取会话详情
fetchScene(sessionId, sceneOrder)       // 获取单个场景
retryScene(sessionId, sceneOrder)       // 重试失败场景
updatePlaybackSnapshot(sessionId, snap) // 保存播放进度
deleteSession(sessionId)                // 删除会话
```

### Pinia 状态管理 (rehearsal.js)

**核心状态：**
```javascript
state: {
  currentSession: { id, title, status },
  scenes: [],                    // 已就绪的场景
  generatingStatus: 'generating|complete|partial|failed|error',
  sceneStatuses: [{ sceneIndex, status, title }],
  spotlightTarget: null,
  highlightTarget: null,
  laserTarget: null,
  currentSubtitle: ''
}
```

**关键 Actions：**
- `startGenerate()` - 开始 SSE 生成
- `loadSession()` - 加载会话详情
- `retryFailedScene()` - 重试失败页面
- `savePlaybackProgress()` - 保存播放进度

---

## 2️⃣ 后端核心 API

### 路由文件：backend/app/api/rehearsal.py

| 方法 | 端点 | 功能 |
|------|------|------|
| POST | `/api/v1/rehearsal/generate-stream` | SSE 流式生成 |
| GET | `/api/v1/rehearsal/sessions` | 获取会话列表 |
| GET | `/api/v1/rehearsal/sessions/{id}` | 获取会话详情 |
| GET | `/api/v1/rehearsal/sessions/{id}/scenes/{order}` | 获取单个场景 |
| POST | `/api/v1/rehearsal/sessions/{id}/scenes/{order}/retry` | 重试页面 |
| PATCH | `/api/v1/rehearsal/sessions/{id}` | 更新播放进度 |
| DELETE | `/api/v1/rehearsal/sessions/{id}` | 删除会话 |

### SSE 事件流

```
event: session_created
data: { "sessionId": 123, "title": "..." }

event: outline_ready
data: { "totalScenes": 7, "outlines": [...] }

event: scene_status
data: { "sceneIndex": 0, "status": "ready|failed", "title": "..." }

event: complete
data: { "sessionId": 123, "status": "ready|partial|failed" }

event: error
data: { "message": "错误信息" }
```

---

## 3️⃣ 后端核心服务

### 生成管线 (rehearsal_generation_service.py)

**4 阶段流程：**

#### Stage 1: 大纲生成
```
调用 LLM → 生成 5-8 个教学场景 → 预创建 RehearsalScene 记录
↓
JSON 格式：
[
  {
    "title": "课程导入",
    "description": "欢迎和课程概览",
    "keyPoints": ["要点1", "要点2"],
    "teachingObjective": "..."
  }
]
```

#### Stage 2: 逐页生成
```
为每个场景：
├─ 生成幻灯片内容 (slide_content)
├─ 生成教学动作序列 (actions)
├─ 调用 populate_slide_media() 生成图片
├─ 估算讲稿时长
└─ 保存到 DB，标记为 "ready"
```

**幻灯片内容结构：**
```json
{
  "id": "slide_0",
  "viewportSize": 1000,
  "viewportRatio": 0.5625,
  "background": { "type": "solid", "color": "#ffffff" },
  "elements": [
    {
      "id": "el_1",
      "type": "text|image|shape",
      "left": 0, "top": 0, "width": 200, "height": 100
    }
  ]
}
```

**动作序列结构：**
```json
[
  {
    "type": "spotlight",
    "elementId": "el_1",
    "dimOpacity": 0.4
  },
  {
    "type": "speech",
    "text": "讲稿内容",
    "duration": 5000,
    "audio_status": "pending|temp_ready|ready|failed",
    "temp_audio_url": "...",
    "persistent_audio_url": "..."
  },
  {
    "type": "highlight",
    "elementIds": ["el_1"],
    "color": "#ff6b6b",
    "opacity": 0.22
  },
  {
    "type": "laser",
    "elementId": "el_1",
    "color": "#ff0000",
    "duration": 1600
  }
]
```

#### Stage 3: TTS 异步补齐（非阻塞）
```
页面 ready → TTS 异步启动
↓
fill_tts_for_scene()：为每个 speech action 补齐音频 URL
```

#### Stage 4: 会话状态汇总
```
计算最终状态：ready | partial | failed
```

### 媒体生成服务 (rehearsal_media_service.py)

**功能：** 使用阿里云 Qwen 文生图生成幻灯片图片

```
遍历 slide_content 的图片元素
├─ 构建生图提示词（考虑上下文）
├─ 调用 Qwen API 生成图片
├─ 下载图片
├─ 上传到 OSS
└─ 如果失败，降级为灰色 shape（不中断流程）
```

### TTS 服务 (tts_service.py)

```python
await synthesize(text, voice, speed, user_id)

返回值：
{
  "temp_audio_url": "...",           # 临时 URL（快速）
  "persistent_audio_url": "...",     # 持久 URL（最终）
  "audio_status": "temp_ready|ready|failed"
}
```

### 会话管理服务 (rehearsal_session_service.py)

```python
compute_session_status(session) -> str
  if generating/pending in statuses:
    return "generating"
  elif all ready:
    return "ready"
  elif all failed:
    return "failed"
  else:
    return "partial"
```

---

## 4️⃣ 数据模型

### RehearsalSession 表

```python
class RehearsalSession:
    id: int
    user_id: int
    title: str                         # "教学主题 - 课堂预演"
    topic: str                         # 用户输入
    status: str                        # generating|partial|ready|failed
    total_scenes: int
    playback_snapshot: dict            # { sceneIndex, actionIndex }
    language: str                      # zh-CN|en-US
    settings: dict                     # { voice, speed, enableTTS }
    created_at: datetime
    
    scenes: List[RehearsalScene]
```

### RehearsalScene 表

```python
class RehearsalScene:
    id: int
    session_id: int
    scene_order: int                   # 页码（0-indexed）
    title: str
    scene_status: str                  # pending|generating|ready|failed
    slide_content: dict                # 幻灯片布局
    actions: list                      # 动作序列
    key_points: list                   # 页面要点
    audio_status: str                  # pending|partial|ready|failed
    created_at: datetime
```

---

## 5️⃣ 文件上传流程

### 课件上传 API (courseware.py)

```
POST /api/v1/courseware/upload
├─ 验证：扩展名 (.pdf, .ppt, .pptx, .doc, .docx, .mp4)
├─ 检查：文件大小 ≤ 50MB
├─ 上传到 OSS
├─ 创建 Courseware 记录
└─ 返回 CoursewareAggregateItem
```

### 通用上传 API (upload.py)

```
POST /api/v1/upload
├─ 调用 oss_service.upload_file()
└─ 返回 { url, file_name, file_type }
```

### OSS 服务 (oss_service.py)

```python
async def upload_file(file, user_id) → { url, file_name, file_type }
async def upload_bytes(content, ext, user_id, prefix) → url
async def delete_file(file_url) → None
```

**OSS 路径格式：**
```
/{user_id}/rehearsal-images/{timestamp}-{random}.{ext}
/{user_id}/courseware/{timestamp}-{random}.{ext}
/{user_id}/materials/{timestamp}-{random}.{ext}
```

---

## 6️⃣ 课件聚合查询

### 获取用户所有课件 (courseware_service.py)

```
GET /api/v1/courseware/all
↓
返回格式：
CoursewareAggregateResponse {
  items: [
    {
      id: "ppt_123" | "lp_456" | "up_789",
      source_type: "ppt" | "lesson_plan" | "uploaded",
      name: "标题",
      file_type: "ppt" | "word" | "pdf" | "mp4",
      file_size: 1024000,
      status: "DRAFT" | "COMPLETED",
      cover_image: "OSS URL",
      updated_at: datetime,
      page_count: 12
    }
  ],
  total: 10
}
```

---

## 7️⃣ PPT 生成相关（可复用）

### PPT 项目模型 (banana_models.py)

```python
class PPTProject:           # PPT 项目
    id, user_id, title, status, creation_type, pages, ...

class PPTPage:              # PPT 页面
    id, project_id, page_number, title, image_url, ...

class PPTTask:              # 异步任务
    id, project_id, task_type, status, ...
```

### PPT 上传与翻新

```
POST /api/v1/ppt/{id}/upload-reference
├─ 解析已有 PPT 文件
├─ 提取页面内容
├─ 调用 LLM 改进描述
├─ 生成新图片
└─ 导出新 PPTX
```

---

## 8️⃣ 快速复用示例

### 复用上传功能

```javascript
import { uploadCourseware } from '@/api/courseware.js'

const file = new File(...)
const result = await uploadCourseware(file, {
  title: '我的素材',
  tags: 'physics',
  remark: '牛顿定律'
})
// result: { id, source_type: 'uploaded
