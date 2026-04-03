# PPT生成模块 - banana-slides 前端适配文档

> **Date:** 2026-03-28
> **Status:** Draft
> **Author:** Claude
> **前置文档:**
> - `docs/superpowers/specs/2026-03-28-ppt-frontend-design.md` — PPT前端设计文档
> - `docs/superpowers/specs/2026-03-26-ppt-banana-integration-design.md` — 后端集成设计文档

## 1. 概述

本文档说明如何将 banana-slides（React + TypeScript + Zustand）的前端实现适配到 AIsystem（Vue 3 + Vite + Pinia）。涵盖组件映射、状态管理映射、API 适配、路由适配和实现要点。

**banana-slides 技术栈（适配来源）：**
- React 18.2 + TypeScript
- React Router DOM v6
- Zustand（状态管理）
- Tailwind CSS（样式）
- 原生 HTML5 Drag API（拖拽，无需安装）
- Axios（HTTP）
- i18next（国际化）

**AIsystem 目标技术栈（适配目标）：**
- Vue 3 + Composition API + JavaScript
- Vue Router
- Pinia（状态管理）
- 普通 CSS（scoped style，不引入 Tailwind）
- 原生 HTML5 Drag API（拖拽，无需安装）
- 现有 `authFetch` / `apiRequest` 封装（HTTP）
- 无 i18n（中文界面）

---

## 2. 组件映射表

### 2.1 页面组件映射

| banana-slides (React) | AIsystem (Vue) | 路由 | 功能说明 |
|-----------------------|----------------|------|---------|
| `Home.tsx` | `PptHome.vue` | `/lesson-prep?tab=ppt` | 欢迎页，3个入口（对话/文件/翻新） |
| `OutlineEditor.tsx` | `PptOutline.vue` | `/lesson-prep?tab=outline` | 大纲编辑 |
| `DetailEditor.tsx` | `PptDescription.vue` | `/lesson-prep?tab=description` | 页面描述编辑 |
| `SlidePreview.tsx` | `PptPreview.vue` | `/lesson-prep?tab=preview` | 预览与导出 |
| `History.tsx` | （复用现有 CoursewareManage） | — | 项目历史列表 |
| `Landing.tsx` | （不使用） | — | 落地页，AIsystem 已有的首页 |
| `SettingsPage.tsx` | （不使用） | — | 设置页，LLM 配置在后端 config |

> **说明：** banana-slides 的对话生成入口（`Home` 中的 idea tab）对应 AIsystem 的 `PptDialog.vue`，但 banana-slides 原生没有对话页，AIsystem 的对话页是扩展功能。

### 2.2 共享组件映射

| banana-slides (React) | AIsystem (Vue) | 说明 |
|-----------------------|----------------|------|
| `components/shared/Button` | 复用 AIsystem 现有 `AppButton` | |
| `components/shared/Input` | 复用 AIsystem 现有 `AppInput` | |
| `components/shared/Textarea` | `MarkdownTextarea.vue` | 支持 Markdown 渲染的文本框 |
| `components/shared/Card` | 复用 AIsystem 现有 `AppCard` | |
| `components/shared/Modal` | 复用 AIsystem 现有 `AppModal` | |
| `components/shared/Loading` | 复用 AIsystem 现有 `AppLoading` | |
| `components/outline/OutlineCard` | `OutlineCard.vue` | 大纲页面卡片 |
| `components/preview/DescriptionCard` | `DescriptionCard.vue` | 描述卡片 |
| `components/preview/SlideCard` | `ThumbnailItem.vue` | 缩略图卡片 |
| `components/shared/AiRefineInput` | `AiRefineInput.vue` | AI 优化输入框 |
| `components/shared/FilePreviewModal` | `FileUploader.vue` | 文件上传与预览 |
| `components/shared/ReferenceFileSelector` | `ReferenceFileList.vue` | 参考文件列表 |
| `components/shared/StatusBadge` | `StatusBadge.vue` | 状态徽章 |
| `components/shared/ConfirmDialog` | 复用 AIsystem 现有 `AppConfirm` | |
| `components/shared/ExportTasksPanel` | `ExportDropdown.vue` | 导出任务面板 |

---

## 3. 状态管理映射（Zustand → Pinia）

### 3.1 Zustand Store 结构（banana-slides）

```typescript
// banana-slides: frontend/src/store/useProjectStore.ts
interface ProjectStore {
  // 当前项目
  currentProject: Project | null
  pages: Page[]
  isLoading: boolean
  error: string | null

  // 生成状态
  generationTasks: Task[]
  streamingContent: string

  // Actions
  initializeProject: (projectId: string) => Promise<void>
  createProject: (data: CreateProjectDTO) => Promise<Project>
  syncProject: () => Promise<void>
  generateOutline: () => Promise<void>
  generateDescriptions: (pageIds?: string[]) => Promise<void>
  regeneratePage: (pageId: string) => Promise<void>
  updatePage: (pageId: string, data: Partial<Page>) => Promise<void>
  reorderPages: (pageIds: string[]) => Promise<void>
  // ... 更多 actions
}
```

### 3.2 Pinia Store 结构（AIsystem）

```javascript
// teacher-platform/src/stores/ppt.js
export const usePptStore = defineStore('ppt', {
  state: () => ({
    // 项目信息
    projectId: null,
    projectStatus: null,

    // 流程控制
    creationType: null,   // 'dialog' | 'file' | 'renovation'

    // 模板与风格
    selectedTemplate: null,
    selectedPresetTemplateId: null,
    templateStyle: '',
    aspectRatio: '16:9',

    // 参考文件
    referenceFiles: [],

    // 大纲数据
    outlineText: '',
    outlinePages: [],

    // 描述数据
    descriptions: {},

    // 对话历史
    sessions: [],

    // 生成进度
    generationProgress: { total: 0, completed: 0, failed: 0 },

    // 错误状态
    error: null,
    errorMessage: null
  }),

  actions: {
    async createProject(data) { ... },
    async fetchProject(projectId) { ... },
    async saveSession(role, content) { ... },
    async fetchSessions(projectId) { ... },
    async parseOutline() { ... },
    async generateDescriptions() { ... },
    addPage(page) { ... },
    deletePage(pageId) { ... },
    updatePage(pageId, data) { ... },
    reorderPages(newOrder) { ... },
    setError(error, message) { ... },
    clearError() { ... },
    resetState() { ... }
  }
})
```

### 3.3 关键映射关系

| Zustand (banana-slides) | Pinia (AIsystem) | 备注 |
|------------------------|------------------|------|
| `currentProject` | `projectId` + `fetchProject()` | 只存 ID，完整数据按需获取 |
| `pages[]` | `outlinePages[]` + `descriptions{}` | 合并了大纲和描述数据 |
| `generationTasks` | `generationProgress` | 简化结构 |
| `streamingContent` | 流式响应通过 SSE 处理 | 不需要 store 持有 |
| `isLoading` | 各页面自行管理 | 或通过 `projectStatus` 判断 |
| `error` | `error` + `errorMessage` | |

---

## 4. API 层适配

### 4.1 banana-slides API 结构（Axios）

```typescript
// banana-slides: frontend/src/api/endpoints.ts
export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 30000,
})

// 拦截器添加 access_code
apiClient.interceptors.request.use(config => {
  const code = localStorage.getItem('access_code')
  if (code) config.headers['X-Access-Code'] = code
  return config
})

// 示例接口
export const projectApi = {
  list: () => apiClient.get('/projects'),
  get: (id: string) => apiClient.get(`/projects/${id}`),
  create: (data: CreateProjectDTO) => apiClient.post('/projects', data),
  update: (id: string, data: UpdateProjectDTO) => apiClient.put(`/projects/${id}`, data),
  delete: (id: string) => apiClient.delete(`/projects/${id}`),
}
```

### 4.2 AIsystem API 结构（复用 `authFetch` / `apiRequest`）

> **不**使用 `$api`，复用现有 `src/api/http.js` 的 `authFetch` 和 `apiRequest`。

```javascript
// teacher-platform/src/api/ppt.js
import { apiRequest, authFetch } from '@/api/http'

const API = '/api/v1/ppt'

export async function createProject(data) {
  return await apiRequest(`${API}/projects`, { method: 'POST', body: JSON.stringify(data) })
}

export async function getProject(id) {
  return await apiRequest(`${API}/projects/${id}`)
}

// 流式接口（返回 ReadableStream，由调用方解析 SSE）
export async function generateDescriptionsStream(projectId) {
  return await authFetch(`${API}/projects/${projectId}/descriptions/generate/stream`, { method: 'POST' })
}
```

### 4.3 接口映射

| banana-slides | AIsystem | 说明 |
|--------------|----------|------|
| `GET /projects` | `GET /projects` | 列出用户项目 |
| `POST /projects` | `POST /projects` | 创建项目 |
| `GET /projects/:id` | `GET /projects/:id` | 获取项目详情 |
| `PUT /projects/:id` | `PUT /projects/:id` | 更新项目 |
| `DELETE /projects/:id` | `DELETE /projects/:id` | 删除项目 |
| `POST /projects/:id/outline/generate` | `POST /projects/:id/outline/generate` | 生成大纲 |
| `POST /projects/:id/descriptions/generate` | `POST /projects/:id/descriptions/generate` | 生成描述 |
| `POST /projects/:id/descriptions/generate/stream` | `POST /projects/:id/descriptions/generate/stream` | 流式生成描述 |
| `POST /projects/:id/images/generate` | `POST /projects/:id/images/generate` | 生成图片 |
| `GET /projects/:id/export/pptx` | `GET /projects/:id/export/pptx` | 导出PPTX |
| `POST /projects/:id/materials/upload` | `POST /projects/:id/materials/upload` | 上传素材 |
| `POST /projects/:id/reference-files` | `POST /projects/:id/reference-files` | 上传参考文件 |
| `GET /projects/:id/tasks` | `GET /projects/:id/tasks` | 获取任务列表 |
| `GET /sessions/:project_id` | `GET /sessions/:project_id` | 获取对话历史 |
| `POST /sessions/:project_id` | `POST /sessions/:project_id` | 写入对话 |

**认证方式变更：**
- banana-slides: `X-Access-Code` header
- AIsystem: `Authorization: Bearer <JWT>` header（通过 `authFetch` / `apiRequest` 统一注入，无需手动添加）

---

## 5. 路由适配

### 5.1 banana-slides 路由（React Router）

```tsx
// banana-slides: frontend/src/App.tsx
<BrowserRouter>
  <Routes>
    <Route path="/" element={<Home />} />
    <Route path="/landing" element={<Landing />} />
    <Route path="/history" element={<History />} />
    <Route path="/settings" element={<SettingsPage />} />
    <Route path="/project/:projectId/outline" element={<OutlineEditor />} />
    <Route path="/project/:projectId/detail" element={<DetailEditor />} />
    <Route path="/project/:projectId/preview" element={<SlidePreview />} />
  </Routes>
</BrowserRouter>
```

### 5.2 AIsystem 路由（Vue Router）

**采用 tab 组件切换模式，不使用子路由。** 复用现有 `LessonPrep.vue` 的 `route.query.tab` 切换逻辑，无需修改 `router/index.js`。

```js
// teacher-platform/src/router/index.js
// 无需改动，复用现有路由：
{
  path: '/lesson-prep',
  component: () => import('../views/LessonPrep.vue'),
  meta: { requiresAuth: true, layout: 'nav' }
}
```

PPT tab 切换在 `LessonPrep.vue` 内部处理：

```js
// LessonPrep.vue
const tabs = [
  { id: 'ppt', label: 'PPT生成' },       // 欢迎页
  { id: 'dialog', label: '对话生成' },   // 对话页
  { id: 'outline', label: '大纲编辑' },  // 大纲页
  { id: 'description', label: '页面描述' }, // 描述页
  { id: 'preview', label: '预览导出' }   // 预览页
]

const currentComponent = computed(() => {
  const map = {
    ppt: LessonPrepPpt,
    dialog: PptDialog,        // 新增
    outline: PptOutline,       // 新增
    description: PptDescription, // 新增
    preview: PptPreview        // 新增
  }
  return map[activeTab.value]
})
```

### 5.3 路由映射关系

| banana-slides 路径 | AIsystem URL | 说明 |
|-------------------|--------------|------|
| `/` | `/lesson-prep?tab=ppt` | 欢迎页（Home → PptHome） |
| `/history` | `/courseware` | 复用课件管理页 |
| `/project/:projectId/outline` | `/lesson-prep?tab=outline` | 大纲编辑 |
| `/project/:projectId/detail` | `/lesson-prep?tab=description` | 描述编辑 |
| `/project/:projectId/preview` | `/lesson-prep?tab=preview` | 预览导出 |
| `/settings` | （不使用） | 设置在后端 config |
| `/landing` | （不使用） | 使用 AIsystem 首页 |

---

## 6. 组件实现要点

### 6.1 PptHome.vue（欢迎页）

**对应 banana-slides：** `Home.tsx`

**关键实现：**

```vue
<!-- PptHome.vue -->
<template>
  <div class="ppt-home">
    <HeroSection />
    <CreationTypeSelector @select="handleCreationTypeSelect" />

    <!-- 对话生成入口 -->
    <DialogCreationForm v-if="selectedType === 'dialog'" @submit="handleDialogCreate" />

    <!-- 文件生成入口 -->
    <FileCreationForm v-if="selectedType === 'file'" @submit="handleFileCreate" />

    <!-- PPT翻新入口 -->
    <RenovationForm v-if="selectedType === 'renovation'" @submit="handleRenovationCreate" />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { usePptStore } from '@/stores/ppt'
import { createProject } from '@/api/ppt'
import HeroSection from '@/components/ppt/HeroSection.vue'
import CreationTypeSelector from '@/components/ppt/CreationTypeSelector.vue'
import DialogCreationForm from '@/components/ppt/DialogCreationForm.vue'
import FileCreationForm from '@/components/ppt/FileCreationForm.vue'
import RenovationForm from '@/components/ppt/RenovationForm.vue'

const router = useRouter()
const pptStore = usePptStore()
const selectedType = ref(null)

async function handleDialogCreate(formData) {
  const project = await createProject({
    creation_type: 'dialog',
    idea_prompt: formData.topic,
    template_style: formData.templateStyle,
    aspect_ratio: formData.aspectRatio
  })
  pptStore.projectId = project.id
  pptStore.creationType = 'dialog'
  router.push({ path: '/lesson-prep', query: { tab: 'dialog' } })
}

async function handleFileCreate(formData) {
  const project = await createProject({
    creation_type: 'file',
    aspect_ratio: formData.aspectRatio
  })
  pptStore.projectId = project.id
  pptStore.creationType = 'file'
  // 上传文件后跳转
  await uploadAndParse(project.id, formData.file)
  router.push({ path: '/lesson-prep', query: { tab: 'outline' } })
}

async function handleRenovationCreate(formData) {
  const project = await createProject({
    creation_type: 'renovation',
    aspect_ratio: formData.aspectRatio
  })
  pptStore.projectId = project.id
  pptStore.creationType = 'renovation'
  await uploadAndParse(project.id, formData.file)
  router.push({ path: '/lesson-prep', query: { tab: 'outline' } })
}
</script>
```

### 6.2 PptOutline.vue（大纲页）

**对应 banana-slides：** `OutlineEditor.tsx`

**关键实现：**

```vue
<!-- PptOutline.vue -->
<template>
  <div class="ppt-outline">
    <div class="outline-editor">
      <div class="left-panel">
        <AiOptimizeInput @submit="handleAiOptimize" />
        <MarkdownTextarea v-model="outlineText" />
        <ReferenceFileList :files="pptStore.referenceFiles" />
      </div>
      <div class="right-panel">
        <ActionBar @add-page="handleAddPage" @generate="handleGenerateOutline" />
        <DraggableOutlineList
          :pages="pptStore.outlinePages"
          @reorder="handleReorder"
          @update-page="handleUpdatePage"
          @delete-page="handleDeletePage"
        />
      </div>
    </div>
    <BottomBar @prev="handlePrev" @next="handleNext" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { usePptStore } from '@/stores/ppt'
import { parseOutline } from '@/api/ppt'
import AiOptimizeInput from '@/components/ppt/AiOptimizeInput.vue'
import MarkdownTextarea from '@/components/ppt/MarkdownTextarea.vue'
import ReferenceFileList from '@/components/ppt/ReferenceFileList.vue'
import ActionBar from '@/components/ppt/ActionBar.vue'
import DraggableOutlineList from '@/components/ppt/DraggableOutlineList.vue'
import OutlineCard from '@/components/ppt/OutlineCard.vue'
import BottomBar from '@/components/ppt/BottomBar.vue'

const router = useRouter()
const pptStore = usePptStore()
const outlineText = ref(pptStore.outlineText)

onMounted(async () => {
  if (!pptStore.projectId) {
    router.push('/lesson-prep/ppt')
  }
})

async function handleGenerateOutline() {
  pptStore.outlineText = outlineText.value
  await pptStore.parseOutline()
  router.push({ path: '/lesson-prep', query: { tab: 'description' } })
}

function handleAddPage() {
  pptStore.addPage({
    pageId: Date.now(),
    orderIndex: pptStore.outlinePages.length,
    title: '新页面',
    points: [],
    part: ''
  })
}

function handleReorder(newOrder) {
  pptStore.reorderPages(newOrder)
}

function handleUpdatePage(pageId, data) {
  pptStore.updatePage(pageId, data)
}

function handleDeletePage(pageId) {
  pptStore.deletePage(pageId)
}

function handlePrev() {
  router.back()
}

function handleNext() {
  router.push({ path: '/lesson-prep', query: { tab: 'description' } })
}
</script>
```

### 6.3 PptDescription.vue（描述页）

**对应 banana-slides：** `DetailEditor.tsx`

**关键实现：**

```vue
<!-- PptDescription.vue -->
<template>
  <div class="ppt-description">
    <TopBar>
      <BackButton @click="router.back()" />
      <AiRefineInput @submit="handleAiRefine" />
      <ProgressIndicator :current="completedCount" :total="totalCount" />
    </TopBar>

    <ActionBar>
      <BatchGenerateButton @click="handleBatchGenerate" :disabled="isGenerating" />
      <SettingsDropdown />
      <ImportExportMenu />
    </ActionBar>

    <div class="description-grid">
      <DescriptionCard
        v-for="page in pptStore.outlinePages"
        :key="page.pageId"
        :page="page"
        :description="pptStore.descriptions[page.pageId]"
        @update="handleUpdateDescription"
        @regenerate="handleRegenerate"
      />
    </div>

    <BottomBar @prev="handlePrev" @next="handleNext" />
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { usePptStore } from '@/stores/ppt'
import { generateDescriptions } from '@/api/ppt'
import TopBar from '@/components/ppt/TopBar.vue'
import BackButton from '@/components/ppt/BackButton.vue'
import AiRefineInput from '@/components/ppt/AiRefineInput.vue'
import ProgressIndicator from '@/components/ppt/ProgressIndicator.vue'
import ActionBar from '@/components/ppt/ActionBar.vue'
import BatchGenerateButton from '@/components/ppt/BatchGenerateButton.vue'
import SettingsDropdown from '@/components/ppt/SettingsDropdown.vue'
import ImportExportMenu from '@/components/ppt/ImportExportMenu.vue'
import DescriptionCard from '@/components/ppt/DescriptionCard.vue'
import BottomBar from '@/components/ppt/BottomBar.vue'

const router = useRouter()
const pptStore = usePptStore()
const isGenerating = ref(false)

const totalCount = computed(() => pptStore.outlinePages.length)
const completedCount = computed(() =>
  Object.values(pptStore.descriptions).filter(d => d.status === 'completed').length
)

async function handleBatchGenerate() {
  isGenerating.value = true
  try {
    await pptStore.generateDescriptions()
  } finally {
    isGenerating.value = false
  }
}

async function handleRegenerate(pageId) {
  // 单个页面重新生成
  await pptStore.generateDescriptions([pageId])
}

function handleUpdateDescription(pageId, data) {
  pptStore.descriptions[pageId] = { ...pptStore.descriptions[pageId], ...data }
}

function handlePrev() {
  router.push({ path: '/lesson-prep', query: { tab: 'outline' } })
}

function handleNext() {
  router.push({ path: '/lesson-prep', query: { tab: 'preview' } })
}
</script>
```

### 6.4 PptPreview.vue（预览页）

**对应 banana-slides：** `SlidePreview.tsx`

**关键实现：**

```vue
<!-- PptPreview.vue -->
<template>
  <div class="ppt-preview">
    <div class="left-panel">
      <ThumbnailList>
        <ThumbnailItem
          v-for="(page, index) in pptStore.outlinePages"
          :key="page.pageId"
          :page="page"
          :index="index"
          :is-active="currentPageIndex === index"
          @click="currentPageIndex = index"
        />
      </ThumbnailList>
    </div>

    <div class="right-panel">
      <Toolbar>
        <EditDescriptionButton @click="handleEditDescription" />
        <RegenerateButton @click="handleRegenerate" />
        <ExportDropdown>
          <button @click="handleExport('pptx')">导出PPTX</button>
          <button @click="handleExport('pdf')">导出PDF</button>
          <button @click="handleExport('images')">导出图片</button>
        </ExportDropdown>
        <ZoomControls
          :zoom="zoom"
          @zoom-in="zoom += 0.1"
          @zoom-out="zoom -= 0.1"
          @fit="fitToWindow"
        />
      </Toolbar>

      <div class="slide-preview-container" :style="{ transform: `scale(${zoom})` }">
        <SlidePreview :page="currentPage" />
      </div>

      <ProgressBar :progress="generationProgress" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { usePptStore } from '@/stores/ppt'
import ThumbnailList from '@/components/ppt/ThumbnailList.vue'
import ThumbnailItem from '@/components/ppt/ThumbnailItem.vue'
import Toolbar from '@/components/ppt/Toolbar.vue'
import SlidePreview from '@/components/ppt/SlidePreview.vue'
import ProgressBar from '@/components/ppt/ProgressBar.vue'
import ZoomControls from '@/components/ppt/ZoomControls.vue'
import ExportDropdown from '@/components/ppt/ExportDropdown.vue'

const router = useRouter()
const pptStore = usePptStore()
const currentPageIndex = ref(0)
const zoom = ref(1)

const currentPage = computed(() => pptStore.outlinePages[currentPageIndex.value])

function handleEditDescription() {
  router.push({ path: '/lesson-prep', query: { tab: 'description' } })
}

async function handleRegenerate() {
  // 重新生当前页面图片
}

async function handleExport(format) {
  const link = document.createElement('a')
  link.href = `${API}/projects/${pptStore.projectId}/export/${format}`
  link.download = `presentation.${format}`
  link.click()
}

function fitToWindow() {
  zoom.value = 1
}
</script>
```

---

## 7. 关键组件实现细节

### 7.1 TemplateSelector.vue（模板选择器）

**对应 banana-slides：** `components/shared/TemplateSelector`（原生 React 组件）

```vue
<!-- TemplateSelector.vue -->
<template>
  <div class="template-selector">
    <div class="template-grid">
      <div
        v-for="template in templates"
        :key="template.id"
        class="template-item"
        :class="{ active: modelValue === template.id }"
        @click="$emit('update:modelValue', template.id)"
      >
        <img :src="template.thumbnail" :alt="template.name" />
        <span class="template-name">{{ template.name }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getPresetTemplates } from '@/api/ppt'

const props = defineProps({
  modelValue: { type: String, default: null }
})
defineEmits(['update:modelValue'])

const templates = ref([])

onMounted(async () => {
  const res = await getPresetTemplates()
  templates.value = res.data
})
</script>
```

### 7.2 OutlineCard.vue（大纲卡片）

**对应 banana-slides：** `components/outline/OutlineCard.tsx`

```vue
<!-- OutlineCard.vue -->
<template>
  <div class="outline-card" :data-page-id="page.pageId">
    <div class="card-header">
      <span class="page-number">{{ page.orderIndex + 1 }}</span>
      <select v-model="localPart" class="part-select" @change="emitUpdate">
        <option value="">无</option>
        <option value="封面">封面</option>
        <option value="内容">内容</option>
        <option value="结尾">结尾</option>
      </select>
      <input v-model="localTitle" class="title-input" @input="emitUpdate" />
      <button class="delete-btn" @click="emitDelete">×</button>
    </div>
    <div class="card-body">
      <ul class="points-list">
        <li v-for="(point, idx) in page.points" :key="idx" class="point-item">
          <span>{{ point }}</span>
          <button class="remove-point" @click="removePoint(idx)">×</button>
        </li>
      </ul>
      <div class="add-point">
        <input
          v-model="newPoint"
          placeholder="添加要点..."
          @keydown.enter="addPoint"
        />
        <button @click="addPoint">+</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  page: { type: Object, required: true }
})
const emit = defineEmits(['update', 'delete'])

const localTitle = ref(props.page.title)
const localPart = ref(props.page.part || '')
const newPoint = ref('')

watch(() => props.page, (newPage) => {
  localTitle.value = newPage.title
  localPart.value = newPage.part || ''
}, { deep: true })

function emitUpdate() {
  emit('update', props.page.pageId, {
    title: localTitle.value,
    part: localPart.value,
    points: props.page.points
  })
}

function addPoint() {
  if (newPoint.value.trim()) {
    props.page.points.push(newPoint.value.trim())
    newPoint.value = ''
    emitUpdate()
  }
}

function removePoint(idx) {
  props.page.points.splice(idx, 1)
  emitUpdate()
}

function emitDelete() {
  emit('delete', props.page.pageId)
}
</script>
```

### 7.3 DescriptionCard.vue（描述卡片）

**对应 banana-slides：** `components/preview/DescriptionCard.tsx`

```vue
<!-- DescriptionCard.vue -->
<template>
  <div class="description-card" :class="statusClass">
    <div class="card-header">
      <span class="page-number">{{ page.orderIndex + 1 }}</span>
      <span class="status-badge" :class="description?.status">
        {{ description?.status || 'pending' }}
      </span>
      <div class="card-actions">
        <button class="edit-btn" @click="isEditing = true">编辑</button>
        <button class="regenerate-btn" @click="emit('regenerate', page.pageId)">重新生成</button>
      </div>
    </div>

    <div class="card-content">
      <div v-if="isEditing" class="edit-mode">
        <textarea v-model="editContent" class="content-textarea" />
        <div class="extra-fields">
          <label>视觉元素: <input v-model="editVisualElement" /></label>
          <label>视觉焦点: <input v-model="editVisualFocus" /></label>
          <label>排版布局: <input v-model="editLayout" /></label>
          <label>备注: <textarea v-model="editSpeakerNotes" /></label>
        </div>
        <button @click="saveEdit">保存</button>
        <button @click="isEditing = false">取消</button>
      </div>
      <div v-else class="view-mode">
        <div class="markdown-content" v-html="renderedMarkdown" />
        <div class="extra-fields-display">
          <div><strong>视觉元素:</strong> {{ description?.visualElement }}</div>
          <div><strong>视觉焦点:</strong> {{ description?.visualFocus }}</div>
          <div><strong>排版:</strong> {{ description?.layout }}</div>
          <div><strong>备注:</strong> {{ description?.speakerNotes }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { marked } from 'marked'

const props = defineProps({
  page: { type: Object, required: true },
  description: { type: Object, default: null }
})
const emit = defineEmits(['update', 'regenerate'])

const isEditing = ref(false)
const editContent = ref('')
const editVisualElement = ref('')
const editVisualFocus = ref('')
const editLayout = ref('')
const editSpeakerNotes = ref('')

const statusClass = computed(() => props.description?.status || 'pending')

const renderedMarkdown = computed(() => {
  if (props.description?.content) {
    return marked(props.description.content)
  }
  return ''
})

function saveEdit() {
  emit('update', props.page.pageId, {
    content: editContent.value,
    visualElement: editVisualElement.value,
    visualFocus: editVisualFocus.value,
    layout: editLayout.value,
    speakerNotes: editSpeakerNotes.value
  })
  isEditing.value = false
}
</script>
```

### 7.4 ChatMessage.vue（对话消息）

**AIsystem 特有组件，banana-slides 无对应**

```vue
<!-- ChatMessage.vue -->
<template>
  <div class="chat-message" :class="role">
    <div class="message-avatar">
      <img v-if="role === 'assistant'" src="@/assets/ai-avatar.png" />
      <span v-else>用户</span>
    </div>
    <div class="message-content">
      <div class="message-bubble" v-html="renderedContent" />
      <div class="message-time">{{ formatTime(createdAt) }}</div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { marked } from 'marked'

const props = defineProps({
  role: { type: String, enum: ['user', 'assistant'], required: true },
  content: { type: String, required: true },
  createdAt: { type: String, required: true }
})

const renderedContent = computed(() => marked(props.content))

function formatTime(timeStr) {
  return new Date(timeStr).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}
</script>
```

---

## 8. 样式适配（Tailwind → 普通CSS）

### 8.1 样式转换规则

| Tailwind 语法 | 普通 CSS 等价 |
|--------------|--------------|
| `flex` | `display: flex;` |
| `flex-col` | `flex-direction: column;` |
| `items-center` | `align-items: center;` |
| `justify-between` | `justify-content: space-between;` |
| `gap-4` | `gap: 1rem;` |
| `p-4` | `padding: 1rem;` |
| `m-4` | `margin: 1rem;` |
| `text-sm` | `font-size: 0.875rem;` |
| `text-gray-500` | `color: #6b7280;` |
| `bg-white` | `background-color: white;` |
| `rounded-lg` | `border-radius: 0.5rem;` |
| `shadow-md` | `box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);` |
| `w-full` | `width: 100%;` |
| `h-screen` | `height: 100vh;` |
| `grid grid-cols-3` | `display: grid; grid-template-columns: repeat(3, 1fr);` |

### 8.2 样式文件结构

```
teacher-platform/src/views/ppt/
├── PptHome.vue         # <style scoped> 内联
├── PptDialog.vue       # <style scoped> 内联
├── PptOutline.vue      # <style scoped> 内联
├── PptDescription.vue  # <style scoped> 内联
└── PptPreview.vue      # <style scoped> 内联

teacher-platform/src/components/ppt/
├── TemplateSelector.vue
├── TextStyleSelector.vue
├── MarkdownTextarea.vue
├── ReferenceFileList.vue
├── DescriptionCard.vue
├── OutlineCard.vue
├── ChatMessage.vue
├── AiRefineInput.vue
├── PresetCapsules.vue
└── *.css               # 共用样式文件（如需要）
```

### 8.3 CSS 变量定义

```css
/* src/assets/css/variables.css */
:root {
  --color-primary: #3b82f6;
  --color-primary-hover: #2563eb;
  --color-success: #10b981;
  --color-warning: #f59e0b;
  --color-error: #ef4444;
  --color-bg: #f9fafb;
  --color-surface: #ffffff;
  --color-border: #e5e7eb;
  --color-text: #111827;
  --color-text-secondary: #6b7280;

  --spacing-xs: 0.25rem;
  --spacing-sm: 0.5rem;
  --spacing-md: 1rem;
  --spacing-lg: 1.5rem;
  --spacing-xl: 2rem;

  --radius-sm: 0.25rem;
  --radius-md: 0.5rem;
  --radius-lg: 0.75rem;

  --shadow-sm: 0 1px 2px 0 rgba(0,0,0,0.05);
  --shadow-md: 0 4px 6px -1px rgba(0,0,0,0.1);
  --shadow-lg: 0 10px 15px -3px rgba(0,0,0,0.1);
}
```

---

## 9. 拖拽排序实现（原生 HTML5 Drag API）

### 9.1 实现方案

使用原生 HTML5 Drag API + Vue 组合式 API，无需额外依赖。

**OutlineCard 拖拽实现：**

```vue
<!-- OutlineCard.vue -->
<template>
  <div
    class="outline-card"
    :class="{ dragging: isDragging }"
    draggable="true"
    @dragstart="handleDragStart"
    @dragend="handleDragEnd"
  >
    <div class="drag-handle">⋮⋮</div>
    <div class="card-body">
      <input v-model="localTitle" @change="emitUpdate" />
      <!-- ... -->
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({ page: { type: Object, required: true } })
const emit = defineEmits(['update', 'delete'])
const isDragging = ref(false)

function handleDragStart(e) {
  isDragging.value = true
  e.dataTransfer.setData('text/plain', props.page.pageId)
  e.dataTransfer.effectAllowed = 'move'
}

function handleDragEnd(e) {
  isDragging.value = false
  e.dataTransfer.clearData()
}
</script>
```

**DraggableOutlineList 容器实现：**

```vue
<!-- DraggableOutlineList.vue -->
<template>
  <div
    class="outline-list"
    @dragover.prevent="handleDragOver"
    @drop="handleDrop"
  >
    <OutlineCard
      v-for="page in localPages"
      :key="page.pageId"
      :page="page"
      :class="{ 'drag-over': dragOverId === page.pageId }"
      @update="(data) => $emit('update-page', page.pageId, data)"
      @delete="$emit('delete-page', page.pageId)"
    />
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({ pages: { type: Array, required: true } })
const emit = defineEmits(['reorder', 'update-page', 'delete-page'])

const localPages = ref([...props.pages])
const dragOverId = ref(null)

watch(() => props.pages, (val) => { localPages.value = [...val] }, { deep: true })

function handleDragOver(e) {
  e.preventDefault()
  e.dataTransfer.dropEffect = 'move'
}

function handleDrop(e) {
  e.preventDefault()
  const draggedId = e.dataTransfer.getData('text/plain')
  const targetId = findTargetId(e.target)
  if (draggedId && targetId && draggedId !== targetId) {
    const oldIndex = localPages.value.findIndex(p => p.pageId === draggedId)
    const newIndex = localPages.value.findIndex(p => p.pageId === targetId)
    const newOrder = [...localPages.value]
    newOrder.splice(oldIndex, 1)
    newOrder.splice(newIndex, 0, localPages.value[oldIndex])
    localPages.value = newOrder
    emit('reorder', newOrder.map(p => p.pageId))
  }
  dragOverId.value = null
}

function findTargetId(dom) {
  const card = dom.closest('[draggable="true"]')
  return card ? card.dataset.pageId : null
}
</script>
```

---

## 10. 流式响应处理（SSE）

### 10.1 banana-slides 流式实现（React）

```typescript
// banana-slides: useStreaming hook
export function useStreaming<T>(url: string, options?: RequestInit) {
  const [data, setData] = useState<T[]>([])
  const [error, setError] = useState<Error | null>(null)

  useEffect(() => {
    const eventSource = new EventSource(url)
    eventSource.onmessage = (e) => {
      const newData = JSON.parse(e.data)
      setData(prev => [...prev, newData])
    }
    return () => eventSource.close()
  }, [url])

  return { data, error }
}
```

### 10.2 AIsystem 流式实现（Vue）

```javascript
// api/ppt.js
export async function* generateDescriptionsStream(projectId) {
  const response = await fetch(
    `${API}/projects/${projectId}/descriptions/generate/stream`,
    {
      method: 'POST',
      headers: {
        ...getAuthHeaders(),
        'Content-Type': 'application/json'
      }
    }
  )

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const event = JSON.parse(line.slice(6))
          yield event
        } catch (e) {
          // 忽略解析错误
        }
      }
    }
  }
}

// 在 PptDescription.vue 中使用
// 按 data.type 分流，不依赖 event 名（统一为 message）
async function handleBatchGenerate() {
  const pptStore = usePptStore()
  for await (const event of generateDescriptionsStream(pptStore.projectId)) {
    switch (event.type) {
      case 'page':
        pptStore.descriptions[event.page_id] = event.content
        break
      case 'progress':
        pptStore.generationProgress = { total: event.total, completed: event.completed, failed: event.failed }
        break
      case 'done':
        // 完成
        break
      case 'error':
        pptStore.setError('error', event.message)
        break
      case 'material_generated':
        // 素材生成完成
        break
      case 'export_task_progress':
        // 导出任务进度更新
        break
      case 'export_task_completed':
        // 导出任务完成
        break
    }
  }
}
```

---

## 11. 实现检查清单

### 11.1 页面组件开发顺序

1. **PptHome.vue** — 欢迎页，三个入口
2. **PptOutline.vue** — 大纲编辑页
3. **PptDescription.vue** — 描述编辑页
4. **PptPreview.vue** — 预览导出页
5. **PptDialog.vue** — 对话页（可选，对话生成入口）

### 11.2 共享组件开发顺序

1. `TemplateSelector.vue`
2. `TextStyleSelector.vue`
3. `MarkdownTextarea.vue`
4. `AiRefineInput.vue`
5. `OutlineCard.vue`
6. `DescriptionCard.vue`
7. `ChatMessage.vue`（对话页用）
8. `ReferenceFileList.vue`
9. `BottomBar.vue`
10. `ThumbnailItem.vue`

### 11.3 依赖安装

```bash
cd teacher-platform
npm install marked       # Markdown 渲染
```

---

## 12. 与现有 AIsystem 的集成点

### 12.1 复用现有组件

| 组件 | 路径 | 用途 |
|------|------|------|
| `AppButton` | `src/components/common/AppButton.vue` | 按钮 |
| `AppInput` | `src/components/common/AppInput.vue` | 输入框 |
| `AppCard` | `src/components/common/AppCard.vue` | 卡片 |
| `AppModal` | `src/components/common/AppModal.vue` | 弹窗 |
| `AppLoading` | `src/components/common/AppLoading.vue` | 加载态 |
| `AppConfirm` | `src/components/common/AppConfirm.vue` | 确认对话框 |
| `AppToast` | `src/components/common/AppToast.vue` | 提示 |

### 12.2 复用的 Store

| Store | 路径 | 用途 |
|-------|------|------|
| `useUserStore` | `src/stores/user.js` | 用户认证状态 |

### 12.3 API 封装复用

> 使用 `src/api/http.js` 的 `apiRequest` 和 `authFetch`，不新增封装。

```javascript
// src/api/ppt.js
import { apiRequest } from '@/api/http'

const API = '/api/v1/ppt'

export function createProject(data) {
  return apiRequest(`${API}/projects`, { method: 'POST', body: JSON.stringify(data) })
}

export function getProject(id) {
  return apiRequest(`${API}/projects/${id}`)
}
```

---

## 13. 原型参考

UI 设计完整参考以下 HTML 原型文件（可直接在浏览器中打开预览）：

| 原型文件 | 对应页面 | 核心功能 |
|---------|---------|---------|
| `prototypes/ppt-home-v4.html` | PptHome | 3个入口tab、模板网格、文字风格切换 |
| `prototypes/ppt-dialog.html` | PptDialog | 意图澄清工作台、置信度看板、快捷按钮 |
| `prototypes/ppt-outline.html` | PptOutline | 双栏布局、大纲卡片拖拽、Part标签 |
| `prototypes/ppt-description.html` | PptDescription | 3列网格、状态badge、设置下拉 |
| `prototypes/ppt-preview.html` | PptPreview | 缩略图列表、大预览区、缩放控制 |

> **实现时**：原型 HTML 中的 CSS 可直接复制到 Vue SFC 的 `<style scoped>` 中，JS 逻辑需转换为 Vue Composition API。

## 14. CSS 变量参考

原型中定义的 CSS 变量，实现时统一复用：

```css
:root {
  --bg-primary: #f0f7ff;
  --bg-card: #ffffff;
  --bg-secondary: #f8fafc;
  --text-primary: #1e293b;
  --text-secondary: #64748b;
  --text-tertiary: #94a3b8;
  --accent: #3b82f6;
  --accent-light: #dbeafe;
  --accent-hover: #2563eb;
  --banana: #F59E0B;
  --banana-light: #fef3c7;
  --success: #10b981;
  --warning: #f59e0b;
  --danger: #ef4444;
  --border: #e5e7eb;
  --border-secondary: #f1f5f9;
  --shadow: 0 1px 3px rgba(0,0,0,0.08);
  --shadow-md: 0 4px 12px rgba(0,0,0,0.1);
  --shadow-lg: 0 8px 32px rgba(0,0,0,0.08);
  --radius: 12px;
  --radius-lg: 16px;
  --radius-xl: 20px;
}
```

## 15. Gap Analysis - banana-slides与原型的功能差异

### 15.1 页面/路由缺失

| banana-slides 路由 | 对应功能 | 原型状态 |
|---|---|---|
| `/history` | 历史项目列表页 | **复用** `/courseware` 课件管理页，不新建 PptHistory |
| `/settings` | 设置页面 | **不采用** - LLM配置在后端config |
| `Landing.tsx` | 落地页 | **不采用** - 使用AIsystem首页 |

### 15.2 组件缺失

| banana-slides 组件 | 功能 | 原型状态 |
|---|---|---|
| `MaterialCenterModal` | 素材中心，管理已生成素材 | **缺失** |
| `MaterialGeneratorModal` | 素材生成弹窗 | **缺失** |
| `ExportTasksPanel` | 导出任务面板（进度/历史） | **缺失** |
| `ProjectSettingsModal` | 项目设置（横竖版切换等） | **缺失** |
| `FilePreviewModal` | 参考文件预览弹窗 | **缺失** |
| `ReferenceFileSelector` | 参考文件选择器 | **缺失** |
| `StatusBadge` | 状态徽章组件 | **缺失** |
| `Pagination` | 分页组件 | **缺失** |

### 15.3 功能缺失明细

#### PptHome (ppt-home-v4.html)
| 缺失功能 | 说明 |
|---|---|
| 模板搜索/过滤 | 模板网格缺少搜索框和分类tab |
| 模板分类tab | 全部/教育/商务/简约等分类 |
| 用户模板管理入口 | 最近使用/收藏的模板 |
| 最近项目快速访问 | 历史项目快速入口 |

#### PptDialog (ppt-dialog.html)
| 缺失功能 | 说明 |
|---|---|
| 对话轮次上限 | maxRound 限制 |
| 草稿大纲一键确认 | draftReady 状态触发确认按钮 |
| 消息重新编辑/删除 | 用户消息的撤回/编辑 |
| 输入框字数统计 | 字符计数显示 |
| 快捷键支持 | Enter发送/Ctrl+Enter换行 |

#### PptOutline (ppt-outline.html)
| 缺失功能 | 说明 |
|---|---|
| AI优化流式输出 | parseOutline 流式响应 |
| Part标签编辑 | 可选择封面/内容/结尾 |
| 页面动画/转场设置 | 每个页面的动画效果 |
| 参考文件解析进度 | parseStatus 状态显示 |
| 参考文件预览 | PDF/图片预览弹窗 |
| 参考文件内容嵌入 | 提取文本显示在侧边 |

#### PptDescription (ppt-description.html)
| 缺失功能 | 说明 |
|---|---|
| 单页描述编辑 | 点击进入编辑模式 |
| 批量操作 | 批量生成/删除/重新生成 |
| 生成模式切换 | 标准/简洁/详细模式 |
| 视觉元素字段编辑 | 完整4字段编辑 |
| 导入/导出描述 | JSON格式导入导出 |
| 生成失败重试 | 单页重试机制 |

#### PptPreview (ppt-preview.html)
| 缺失功能 | 说明 |
|---|---|
| 缩略图布局切换 | 垂直/水平布局 |
| 页面备注预览 | speakerNotes 显示 |
| 版本历史下拉 | PageImageVersion 数据 |
| 重新生成单页 | 单页面图片重新生成 |
| 编辑后保存 | 修改后的保存逻辑 |

### 15.4 Store状态缺失

| 缺失状态 | 说明 |
|---|---|
| `materials` | 素材列表 |
| `exportTasks` | 导出任务列表 |
| `projectSettings` | 项目设置 |
| `referenceFiles[].parseStatus` | 解析状态 |
| `referenceFiles[].markdownContent` | 解析后内容 |
| `pages[].imageVersions` | 图片版本历史 |
| `userTemplates` | 用户模板 |

### 15.5 SSE事件类型缺失

| 事件类型 | 说明 |
|---|---|
| `material_generated` | 素材生成完成 |
| `export_task_progress` | 导出进度 |
| `export_task_completed` | 导出完成 |

---

## 16. 已知差异与注意事项

1. **React → Vue 语法差异**：所有 React JSX 需转换为 Vue 模板语法，`.map()` 转为 `v-for`，`.filter()` 转为计算属性
2. **Zustand → Pinia**：状态声明和 actions 写法完全不同，需重写
3. **Tailwind → 普通 CSS**：banana-slides 大量使用 Tailwind 类名，需转换为普通 CSS
4. **React DnD → Vue DnD**：使用原生 HTML5 Drag API，无需额外依赖
5. **SSE 实现**：banana-slides 用 EventSource，Vue 版本需用 fetch + ReadableStream
6. **i18n**：banana-slides 有 i18next，AIsystem 无 i18n，直接写中文
7. **banana-slides 无对话页**：AIsystem 的 `PptDialog.vue` 是新增功能，需自行实现对话逻辑
