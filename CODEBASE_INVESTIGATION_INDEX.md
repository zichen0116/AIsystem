# 课堂预演（课堂预演）代码分析索引

## 📄 文档位置

本次调查生成了 **两份详细分析文档**：

### 1. **REHEARSAL_ANALYSIS.md** （9.6 KB）
**完整技术分析** - 详细的架构和实现细节
- 10 个章节，包含代码结构、数据模型、API 设计、服务实现
- 适合：深入理解系统、开发新功能、代码审查
- 包含：前端结构、后端 API、生成流程、数据模型、上传流程、PPT 参考、复用示例、创意实现、调试监控、开发清单

### 2. **FINDINGS_SUMMARY.txt** （5.0 KB）
**快速参考指南** - 核心要点和关键文件位置
- 结构化总结，易于快速查阅
- 适合：快速入门、文件映射、流程概览
- 包含：文件位置、生成流程、关键创意、API 端点、上传流程、可复用模块、数据模型

---

## 🔍 核心发现概览

### 前端组件（Vue 3 + Pinia）
| 文件 | 功能 | 行数 |
|------|------|------|
| RehearsalNew.vue | 生成界面（表单→SSE→轮询） | 1052 |
| RehearsalPlay.vue | 播放界面（幻灯片+视觉效果） | 400+ |
| SlideRenderer.vue | Canvas 幻灯片渲染 | - |
| rehearsal.js (api) | 7 个 API 函数 | 49 |
| rehearsal.js (store) | Pinia 状态管理 | 340 |

### 后端服务（FastAPI + SQLAlchemy）
| 文件 | 功能 | 行数 |
|------|------|------|
| rehearsal_generation_service.py | 4 阶段生成管线 | 726 |
| rehearsal_media_service.py | Qwen 文生图 + OSS | 300 |
| tts_service.py | 文语合成（阿里云） | ~100 |
| rehearsal_session_service.py | 会话管理 | ~150 |
| rehearsal.py (api) | 7 个 HTTP 端点 | 96 |

### 数据模型（PostgreSQL）
| 表名 | 用途 | 字段数 |
|------|------|--------|
| rehearsal_sessions | 预演会话 | 11 |
| rehearsal_scenes | 预演场景（页面） | 11 |

---

## 🎯 关键技术亮点

### 1. 生成流程（4 阶段）
```
大纲生成 → 逐页生成 → TTS 异步补齐 → 状态汇总
    ↓          ↓           ↓            ↓
  LLM      幻灯片+动作  音频非阻塞   ready/partial/failed
         (含生图+动作)
```

### 2. 异步 TTS 非阻塞设计
```
页面 ready (DB) → 响应前端 → 异步启动 TTS → 更新音频 URL
优势：页面更快就绪，播放时自动使用最新音频
```

### 3. 页级动作系统（4 种）
```
speech    → 讲解（含音频 URL）
spotlight → 聚焦（暗化周围元素）
highlight → 高亮（边框+透明填充）
laser     → 激光笔（脉冲动画）
```

### 4. 可视效果层次化渲染
```
Canvas (幻灯片)
  ├─ SpotlightOverlay (暗化蒙版)
  ├─ HighlightOverlay (边框+填充)
  └─ LaserPointer (动画点)
```

### 5. 页位置感知讲稿规范化
```
首页：保留 "同学们好"、"今天我们来学习"
非首页：去除重复开场白，自然承接前一页
```

---

## 📍 核心文件位置速查

### 前端
```
teacher-platform/src/
├── views/rehearsal/
│   ├── RehearsalNew.vue          🌟 生成界面
│   └── RehearsalPlay.vue         🌟 播放界面
├── components/rehearsal/
│   ├── SlideRenderer.vue         🌟 幻灯片渲染
│   ├── PlaybackControls.vue
│   ├── SpotlightOverlay.vue
│   ├── HighlightOverlay.vue
│   └── LaserPointer.vue
├── api/rehearsal.js              🌟 API 封装（7 个函数）
└── stores/rehearsal.js           🌟 Pinia 状态（10+ actions）
```

### 后端
```
backend/app/
├── api/
│   ├── rehearsal.py              🌟 7 个 HTTP 端点
│   ├── courseware.py             🌟 文件上传
│   └── upload.py
├── services/
│   ├── rehearsal_generation_service.py    🌟 4 阶段生成（726 行）
│   ├── rehearsal_media_service.py         🌟 文生图（300 行）
│   ├── rehearsal_session_service.py       🌟 会话管理
│   ├── tts_service.py                    🌟 语音合成
│   ├── oss_service.py                    🌟 文件存储
│   └── courseware_service.py             🌟 课件聚合
├── models/
│   ├── rehearsal.py              🌟 2 个数据表
│   └── courseware.py             🌟 课件表
└── generators/ppt/
    └── banana_models.py          🌟 PPT 模型（可参考）
```

---

## 🚀 快速开发指南

### 1. 了解整体架构
**文档：** REHEARSAL_ANALYSIS.md 第 1-3 章

### 2. 理解生成流程
**文档：** REHEARSAL_ANALYSIS.md 第 3.1 章（4 阶段详解）
**代码：** backend/app/services/rehearsal_generation_service.py 第 530-641 行

### 3. 复用已有功能

#### 复用上传
```javascript
import { uploadCourseware } from '@/api/courseware.js'
const result = await uploadCourseware(file, { title, tags, remark })
```

#### 复用 TTS
```python
from app.services.tts_service import synthesize
result = await synthesize(text, voice, speed, user_id)
# → { temp_audio_url, persistent_audio_url, audio_status }
```

#### 复用生图
```python
from app.services.rehearsal_media_service import populate_slide_media
updated = await populate_slide_media(slide_content, outline, user_id, session_id, scene_id)
```

### 4. 检查清单

新增功能时：
- [ ] 前端 Route（Vue Router）
- [ ] API Endpoint（FastAPI）
- [ ] Pinia Action（状态管理）
- [ ] Backend Service（业务逻辑）
- [ ] Database Model（如需持久化）
- [ ] Database Migration（Alembic）
- [ ] Error Handling（前后端错误处理）
- [ ] Unit Tests（单元测试）

---

## 💡 可复用的模块化设计

### ✅ 独立服务
| 服务 | 位置 | 功能 |
|------|------|------|
| TTS | tts_service.py | 文本→音频 URL |
| 生图 | rehearsal_media_service.py | 提示词→图片 URL |
| 上传 | oss_service.py | 文件→OSS URL |
| 课件聚合 | courseware_service.py | PPT+教案+上传文件聚合查询 |

### ✅ PPT 生成架构可参考
- **文件：** backend/app/generators/ppt/banana_models.py
- **用途：** PPTProject、PPTPage、PPTTask 等模型
- **特点：** 异步任务管理、页面版本控制、翻新支持

---

## 📊 API 端点速查

```
POST   /api/v1/rehearsal/generate-stream           SSE 流式生成
GET    /api/v1/rehearsal/sessions                  会话列表
GET    /api/v1/rehearsal/sessions/{id}             会话详情（含所有场景）
GET    /api/v1/rehearsal/sessions/{id}/scenes/{order}    单个场景
POST   /api/v1/rehearsal/sessions/{id}/scenes/{order}/retry    重试场景
PATCH  /api/v1/rehearsal/sessions/{id}             更新播放进度
DELETE /api/v1/rehearsal/sessions/{id}             删除会话

POST   /api/v1/courseware/upload                   上传课件
GET    /api/v1/courseware/all                      课件聚合列表
POST   /api/v1/upload                              通用文件上传
```

---

## 📈 数据流

### 生成流程
```
前端 (RehearsalNew.vue)
    ↓
API: generateRehearsalStream(params)  [SSE]
    ↓
后端 (rehearsal_generation_service.py)
    ├─ Stage 1: 生成大纲 (LLM)
    ├─ Stage 2: 逐页生成 (LLM + 文生图 + TTS)
    ├─ Stage 3: 状态汇总
    └─ DB: rehearsal_sessions, rehearsal_scenes
    ↓
SSE Events → 前端 Pinia Store
    ↓
轮询 API: fetchSession(sessionId)  [增量获取]
    ↓
前端 UI 更新
```

### 播放流程
```
前端 (RehearsalPlay.vue)
    ↓
API: loadSession(sessionId)
    ↓
后端 DB: rehearsal_sessions, rehearsal_scenes
    ↓
Pinia Store: scenes[], currentScene, actions[]
    ↓
播放引擎 (usePlaybackEngine.js)
    ├─ 按顺序执行 actions
    ├─ 显示讲稿 (speech action)
    ├─ 应用视觉效果 (spotlight/highlight/laser)
    └─ 播放音频 (speech.audio_url)
    ↓
Canvas 渲染 + Overlay 合成
```

---

## 🔗 关键实现细节

### SSE 事件流格式
```
event: session_created
data: { "sessionId": 123, "title": "..." }

event: outline_ready
data: { "totalScenes": 7, "outlines": [...] }

event: scene_status
data: { "sceneIndex": 0, "sceneId": 456, "status": "ready|failed", "title": "..." }

event: complete
data: { "sessionId": 123, "status": "ready|partial|failed" }

event: error
data: { "message": "错误信息" }
```

### 幻灯片内容结构
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
      "left": 0, "top": 0, "width": 200, "height": 100,
      ...
    }
  ]
}
```

### 动作序列结构
```json
[
  { "type": "spotlight", "elementId": "el_1", "dimOpacity": 0.4 },
  { "type": "speech", "text": "讲稿", "duration": 5000, "audio_status": "ready", "temp_audio_url": "...", "persistent_audio_url": "..." },
  { "type": "highlight", "elementIds": ["el_1"], "color": "#ff6b6b" },
  { "type": "laser", "elementId": "el_1", "color": "#ff0000", "duration": 1600 }
]
```

### 会话状态计算逻辑
```python
if 'generating' or 'pending' in statuses:
    return "generating"
elif all 'ready':
    return "ready"
elif all 'failed':
    return "failed"
else:
    return "partial"  # 混合状态
```

---

## 📚 相关文档推荐阅读顺序

1. **FINDINGS_SUMMARY.txt** （5 分钟）- 快速概览
2. **REHEARSAL_ANALYSIS.md** 第 1-2 章 （10 分钟）- 架构理解
3. **REHEARSAL_ANALYSIS.md** 第 3-4 章 （20 分钟）- 核心服务和数据模型
4. **源代码** - RehearsalNew.vue + rehearsal_generation_service.py （深入学习）

---

## 🎓 学习资源

### 前端技术
- Vue 3 Composition API
- Pinia 状态管理
- SSE（Server-Sent Events）与轮询混合
- Canvas 2D 渲染

### 后端技术
- FastAPI 异步框架
- SQLAlchemy ORM
- PostgreSQL JSONB 存储
- Asyncio 并发编程

### 第三方服务
- 阿里云百炼 Qwen 文生图 API
- 阿里云 OSS（对象存储）
- TTS 服务（文字转语音）

---

## 📝 文档元数据

| 项目 | 值 |
|------|-----|
| 生成时间 | 2026-04-12 |
| 覆盖范围 | 课堂预演完整功能（生成、播放、上传、媒体） |
| 主要文件数 | 25+ |
| 代码行数 | 2000+ |
| 数据表数 | 2 |
| API 端点数 | 7 |

---

## ❓ 常见问题

**Q: 页面生成速度如何优化？**
A: 见 REHEARSAL_ANALYSIS.md 第 3.2 章 - 异步 TTS 非阻塞设计

**Q: 如何支持新的讲解动作类型？**
A: 见 REHEARSAL_ANALYSIS.md 第 8.1 章 - 页级动作系统

**Q: 如何复用上传功能到新功能？**
A: 见 REHEARSAL_ANALYSIS.md 第 10.1 章 - 快速复用示例

**Q: 前端和后端如何同步数据？**
A: 见本文档"数据流"部分 - SSE + 轮询混合方案

---

**更多问题？** 查阅完整分析文档 REHEARSAL_ANALYSIS.md
