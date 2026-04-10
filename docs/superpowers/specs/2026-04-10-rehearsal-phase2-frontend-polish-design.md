# 课堂预演第二阶段：前端渲染与页面打磨设计

## 概述

基于第一阶段已落地的课堂预演 MVP，进行前端页面结构整理、入口承接和交互打磨。核心目标是将"能跑"的预演能力整理为更像正式产品的教师端页面体验。

**范围**：纯前端工作，不涉及后端改动。

## 页面结构与路由

### 路由变更

| 路由 | 页面 | 布局 | 操作 |
|------|------|------|------|
| `/rehearsal` | `RehearsalLab.vue` | LayoutWithNav（带侧边栏） | **新建** |
| `/rehearsal/new` | `RehearsalNew.vue` | LayoutWithNav（带侧边栏） | **保留，小改** |
| `/rehearsal/play/:id` | `RehearsalPlay.vue` | 无侧边栏（全屏） | **保留，改造** |
| `/rehearsal/history` | `RehearsalHistory.vue` | — | **删除** |

### 侧边栏入口

在 `LayoutWithNav.vue` 中添加一级菜单项「课堂预演」：
- 位置：「课件管理」之后、「知识库」之前
- 路由：`/rehearsal`
- 图标：Element Plus `VideoPlay` 图标

### 用户流程

```
侧边栏「课堂预演」→ Lab 页（输入主题）→ 点确认 → New 页（生成进度）→ 完成 → 点"开始播放" → Play 页
Lab 页「我的课程」卡片 → status=ready → 直接 Play 页
Lab 页「我的课程」卡片 → status=generating/partial → New 页查看进度
```

## RehearsalLab 页面设计（新建）

### 视觉风格

严格按 lesson-pre.md 设计：
- 页面背景：浅白色基底 + 淡粉色柔和渐变
- 全局采用毛玻璃 UI，大圆角（16px+）设计
- 字体：现代无衬线字体
- 主色：粉色 + 深灰，辅助色：浅粉 + 黄色

### 模块结构（从上到下，水平居中）

#### 1. 品牌 Logo 区

- 左侧：几何立方体风格双色图标（粉色 + 黄色）
- 右侧：文字「Lesson」深灰/黑色 +「Rehearsal」粉色加粗

#### 2. 核心输入卡片

- 容器：大圆角（16px+）、浅白色毛玻璃背景、轻微阴影
- 顶部：默认圆形用户头像 +「嗨，老师」+ 下拉箭头
- 主体：大输入框，placeholder 灰色示例文字：
  ```
  输入您要预演的教学主题，例如：
  「中国历史文化发展课程预演」
  「数据结构红黑树课程预演」
  ```
- 底部左：附件图标 + 麦克风图标（仅 UI 占位，点击 toast「敬请期待」）
- 底部右：粉色圆角「确认」按钮（白色文字）
- 确认行为：携带主题跳转到 `/rehearsal/new?topic=xxx`

#### 3.「我的课程」区域

- 标签栏：「我的课程」标签（选中态，下划线高亮）
- 课程卡片：水平排列，圆角矩形、白色背景、轻微阴影
- 单卡结构：
  - 顶部：课程标题（深色字体）
  - 主体：课程要点/场景列表（灰色小字）
  - 底部左：页数 + 日期（浅粉色字体）
  - 底部右：状态标签
- 数据来源：rehearsal store 的 `loadSessions()` 接口
- 状态标签样式：
  - `ready`：绿色标签「已就绪」
  - `generating`：蓝色标签 + 动画「生成中」
  - `partial`：橙色标签「部分完成」
  - `failed`：红色标签「生成失败」
- 卡片点击行为：
  - `ready` → `/rehearsal/play/:id`
  - `generating` / `partial` → `/rehearsal/new?sessionId=xxx`
  - `failed` → `/rehearsal/new?sessionId=xxx`
- 卡片操作：删除按钮（带确认弹窗）
- 空状态：居中提示「还没有课程，输入主题开始预演吧」
- 加载状态：骨架屏

## RehearsalPlay 播放页改造

### 整体风格

参考 playback.md，深色主题，视觉层次清晰。

### 顶部栏

- 左：返回箭头 +「当前场景」灰色文字
- 中：当前场景标题（加粗居中）

### 课件展示区

- 深灰/炭灰圆角卡片容器
- SlideRenderer 渲染在卡片内部
- SpotlightOverlay / LaserPointer 叠加在卡片内
- 加载状态：骨架屏 + loading 动画
- 错误状态：错误提示 + 「重试」按钮

### 底部控制栏（重新设计）

- 布局：上一页 | 播放/暂停 | 下一页 | 场景进度条 | 全屏按钮
- 场景进度条：显示当前第 N/M 页，可点击跳转到指定场景
- 全屏按钮：触发浏览器全屏 API（`document.documentElement.requestFullscreen()`）

### 字幕区

- 保留当前 SubtitlePanel 暗色主题字幕条
- 简洁风格，不加头像/聊天气泡

### 状态处理

- 页面加载中：全屏居中 loading spinner
- 会话不存在/加载失败：错误提示 + 返回按钮
- 场景无音频：静默播放，字幕正常显示，计时器推进

## RehearsalNew 生成进度页调整

- 支持 URL query 参数：
  - `?topic=xxx`：从 Lab 页跳转，自动开始生成
  - `?sessionId=xxx`：从 Lab 页点击已有卡片跳转，加载已有会话进度
- 当 `sessionId` 存在时，加载已有会话的生成状态而非创建新的
- **实时刷新机制**：当从已有 sessionId 进入且会话状态为 `generating` 时，使用轮询 `GET /api/v1/rehearsal/sessions/:id`（间隔 3 秒）持续刷新场景状态，直到会话状态变为 `ready` / `partial` / `failed` 后停止轮询
- 生成完成后「开始播放」按钮跳转到 `/rehearsal/play/:id`
- 视觉保持当前 Element Plus 风格，不做大改

## 删除/清理

- 删除 `src/views/rehearsal/RehearsalHistory.vue`
- 删除 `/rehearsal/history` 路由配置
- 清理任何对 history 路由的引用

## 改动文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `src/views/rehearsal/RehearsalLab.vue` | 新建 | Lab 入口页，毛玻璃风格 |
| `src/views/rehearsal/RehearsalPlay.vue` | 改造 | 播放页视觉打磨 |
| `src/views/rehearsal/RehearsalNew.vue` | 小改 | 支持 query 参数 |
| `src/views/rehearsal/RehearsalHistory.vue` | 删除 | 功能合并到 Lab 页 |
| `src/components/rehearsal/PlaybackControls.vue` | 改造 | 加进度条 + 全屏 |
| `src/components/LayoutWithNav.vue` | 小改 | 加一级菜单「课堂预演」 |
| `src/router/index.js` | 改 | 加 /rehearsal，删 /rehearsal/history |
| `src/stores/rehearsal.js` | 小改 | 确保 Lab 页历史列表加载 |

## 不做的事项

- 不做 PPT 生成→预演的入口引导（第三阶段）
- 不做附件上传、语音输入功能（仅 UI 占位）
- 不扩展 SlideRenderer 元素类型
- 不改后端接口或数据模型
- 不做倍速、音量控制
