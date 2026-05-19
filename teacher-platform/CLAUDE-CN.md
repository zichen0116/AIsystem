# CLAUDE-CN.md

本文件用于指导 Claude Code (claude.ai/code) 在本仓库工作。

## 项目概述

多模态 AI 教学平台的 Vue 3 + Vite 前端，与 `../backend/` 下的 FastAPI 后端配套。主要功能：备课中心（PPT / 教案 / 动画 / 知识图谱 / 思维导图 / 数据分析）、课件管理、知识库 RAG、试题生成、课堂预演播放器、数字人助手、管理后台。

## 常用命令

```bash
npm install                              # 安装依赖
npm run dev                              # 启动 vite 开发服务器（默认 :5173）
npm run build                            # 生产构建 → dist/
npm run preview                          # 预览构建产物
npm run test                             # vitest 单次运行
npm run test:watch                       # vitest 监听模式
npx vitest run src/api/http.spec.js      # 运行单个测试文件
npx vitest run -t "buildApiUrl"          # 按用例名过滤
```

开发服务器默认后端在 `http://localhost:8000`。Vite 代理（见 `vite.config.js`）会转发 `/api`、`/media`、`/vmss`（讯飞数字人）、`/individuation` 到对应主机——代码中**不要**使用后端绝对 URL，始终走相对路径，让代理生效。

## 架构

### 启动与全局插件

`src/main.js` 注册 **Pinia**、**Vue Router**、**Element Plus**（locale: zh-CN）、**@kjgl77/datav-vue3**。全局样式在 `src/style.css`。`@` 别名指向 `src/`。

### 路由与认证拦截

`src/router/index.js` 使用 `createWebHistory`，所有视图均按需懒加载。带 `meta.requiresAuth` 的路由由唯一一个 `beforeEach` 守卫处理：

1. 首次导航时，如果 localStorage 中存在 token，先调用 `userStore.fetchUser()` 恢复 `userInfo`，然后再判断是否放行。
2. 未登录用户重定向到 `/login?redirect=<原路径>`。

带 `meta.layout === 'nav'` 的路由会渲染在 `LayoutWithNav`（侧栏 + 顶部导航）内；其余路由直接渲染。`App.vue` 通过 computed 切换布局组件。

### API 层

`src/api/http.js` 是所有 HTTP 请求的统一入口，请不要用裸 `fetch`：

- `apiRequest(path, opts)` —— JSON in/out，非 2xx 时抛出解析后的 `detail`。
- `authFetch(path, opts)` —— 返回原始 `Response`（用于流式 / SSE / 文件下载）。
- `buildApiUrl` / `resolveApiUrl` —— 遵循 `VITE_API_BASE`（开发为 `/api` 走代理，生产为绝对 URL）。
- 两者均会自动从 localStorage 取出 token 并附加 `Authorization: Bearer <token>`。非 auth 接口出现 `401` 时会自动清除 token 并跳转 `/login`——**不要**自己再写 401 处理。

功能模块（`courseware.js`、`ppt.js`、`rehearsal.js`、`download.js`）建立在其之上，导出具名函数。`ppt.js` 还提供 `streamEvents(url, opts)`，一个基于 `authFetch` 的 SSE 异步生成器，用于所有 PPT 生成流。

### 状态（Pinia）

`src/stores/` 目录：

- `user.js` —— 认证、2FA、个人资料、token 生命周期（登录态的唯一来源）。
- `ppt.js` —— PPT 项目 + 聊天 + 意图状态机。引用 `@/utils/pptIntent.js`（意图阶段解析）与 `@/utils/pptPlanningContext.js`。
- `courseware.js`、`knowledge.js`、`rehearsal.js`、`adminDigitalHuman.js` —— 各功能模块作用域。

组件直接 import store；不要通过 props 透传 store 数据超过一层——在子组件里重新 import。

### 视图结构

- `src/views/LessonPrep.vue` 是备课中心壳子，切换不同 tab（PPT / 教案 / 动画 / 知识 / 思维导图 / 数据），通过 `resetKeys` 强制重挂载对应视图。
- 每个备课 tab 是一个顶层视图（`LessonPrepPpt`、`LessonPlanPage` 等）。
- `src/views/ppt/` 是自包含的 PPT 生成流程（`PptIndex` → `PptHome` → `PptDialog` → `PptDescription` → `PptOutline` → `PptPreview`，外加 `PptHistory`）。
- `src/views/admin/` 是管理员视图，在 `LayoutWithNav` 中通过 `userStore.userInfo?.is_admin` 控制可见。
- `src/views/rehearsal/` 是预演实验室 / 新建 / 播放界面；播放引擎和特效在 composables 中（`usePlaybackEngine`、`rehearsalPlaybackEffects`）。

### 组件

- `src/components/lesson-plan-v2/` —— 基于 TipTap 的教案编辑器（聊天 + 编辑器 + 侧栏 + 浮动工具栏）。
- `src/components/knowledge-graph/` —— 图谱搜索/筛选 UI，配合 `useKnowledgeGraph` composable 与 3d-force-graph / dagre。
- `src/components/rehearsal/` —— 播放器的幻灯片 / 激光笔 / 聚光 / 字幕等覆盖层。
- `src/components/BigScreen/` —— 基于 datav-vue3 + ECharts 的管理大屏小组件。
- `src/components/DigitalHumanAssistant.vue` —— 悬浮讯飞虚拟人，使用 `src/libs/avatar-sdk-web_3.1.2.1002/` 中的 SDK。

### 重型依赖（按需加载）

- TipTap（富文本）—— 仅教案编辑器
- ECharts + datav-vue3 —— 管理大屏
- 3d-force-graph + three.js —— 知识图谱
- @vue-flow —— 思维导图编辑器
- markmap-lib / markmap-view —— markmap 渲染
- html2pdf.js、html-to-image、@resvg/resvg-wasm —— 导出
- lottie-web —— 动画

让重型 import 保持在各自视图内或使用 `defineAsyncComponent`，确保路由级代码分包。

## 测试

Vitest + jsdom（`src/test/setup.js` 注入 `scrollY`、`innerHeight`、`scrollTo` 的 polyfill）。`*.spec.js` / `*.test.js` 与源码同目录。`@vue/test-utils` 可用于组件测试。提交前先跑相关单测，再跑全量。

## 约定

- 组件 `PascalCase.vue`；composable 命名 `useXxx.js`；store 用 camelCase。
- 跨目录 import 一律使用 `@/` 别名（如 `@/api/http`、`@/utils/pptIntent`）。
- 所有后端调用走 `apiRequest` / `authFetch` —— 不要拼绝对 URL，也不要手动加认证头。
- 默认 UI 组件库为 Element Plus，优先使用其组件而不是自己造。
- Vue SFC 顺序：`<script setup>` → `<template>` → `<style scoped>`（与现有代码风格一致）。
