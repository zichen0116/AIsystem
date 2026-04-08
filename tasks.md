# PPT 文件生成 + PPT 翻新前端需求文档

## 1. 背景

当前 PPT 模块前端已经有三种入口：

- 对话生成
- 文件生成
- PPT 翻新

其中：

- **PPT 文件生成后端** 已经单独立项梳理并完成后端能力
- **PPT 翻新后端** 也已经完成后端能力

但前端仍未真正接入这两条后端链路，导致首页虽然已经有“文件生成”和“PPT 翻新”模式，实际行为仍不完整：

1. `file` 模式下，前端只是普通 `createProject(data)`，并没有真正走“上传文件/粘贴文本 -> 后端自动解析 -> 自动得到大纲”的文件生成流程。
2. `renovation` 模式下，前端虽然已有部分 API 封装和 Preview 单页重试能力，但首页仍没有真正用上传文件创建翻新项目，也没有完整接任务轮询与失败页提示。

本次任务目标是把这两条前端链路统一打通，并继续复用现有 PPT 页面体系，不重做整套 UI。

## 2. 总体目标

在不大改现有 UI 风格和页面结构的前提下，实现两个真正可用的前端流程：

### 2.1 文件生成前端流程

支持用户：

- 上传单个文档文件生成 PPT
- 或粘贴文本生成 PPT
- 或文件 + 文本共同参考生成 PPT
- 要支持拖拽上传文件

并在后端自动生成结构化大纲后，直接进入可编辑的大纲页。

### 2.2 PPT 翻新前端流程

支持用户：

- 上传 PDF/PPT/PPTX 创建翻新项目
- 自动轮询翻新任务
- 在大纲页/描述页/预览页看到翻新解析结果
- 对失败页进行单页重试
- 要支持拖拽上传文件

## 3. 设计原则

本次前端需求遵循以下原则：

1. **不大改现有 UI 风格。**
2. **优先复用现有 PPT 页面结构与 store。**
3. **文件生成和 PPT 翻新都是 PPT 流程的特殊入口，不单独造两套前端系统。**
4. **以功能能跑通、能演示为主，不做过度设计。**
5. **不为了这次需求引入复杂的新状态管理方案。**

## 4. 范围

### 4.1 本次必须完成

- 首页 `file` / `renovation` 两种入口真正可用
- 文件生成 API 接入
- 翻新 API 接入
- store 增加文件生成与翻新任务态
- 文件生成 / 翻新任务轮询
- 大纲页、描述页、预览页状态识别
- 历史项目恢复文件生成和翻新项目
- 单页翻新重试 UI 串联



## 5. 需要改动的前端文件

建议重点修改：

- `teacher-platform/src/api/ppt.js`
- `teacher-platform/src/stores/ppt.js`
- `teacher-platform/src/views/ppt/PptHome.vue`
- `teacher-platform/src/views/ppt/PptIndex.vue`
- `teacher-platform/src/views/ppt/PptOutline.vue`
- `teacher-platform/src/views/ppt/PptDescription.vue`
- `teacher-platform/src/views/ppt/PptPreview.vue`
- `teacher-platform/src/views/ppt/PptHistory.vue`

## 6. 当前前端现状

### 6.1 Home 页面

文件：`teacher-platform/src/views/ppt/PptHome.vue`

当前已经有：

- 三个 mode tab：`dialog / file / renovation`
- 文本输入框
- 本地参考文件选择
- 模板与风格选择

但问题是：

1. 当前 `handleNext()` 不区分 `file` 和 `renovation` 的真实后端流程。
2. 无论是 `file` 还是 `renovation`，现在本质上都还是普通 `createProject(data)`。
3. `uploadedReferenceFiles` 现在只是前端本地暂存，并没有真正参与项目创建链路。

### 6.2 API 层

文件：`teacher-platform/src/api/ppt.js`

当前已有：

- `uploadReferenceFile(projectId, file)`
- `parseReferenceFile(projectId, fileId)`
- `createRenovationProject(file)`
- `regeneratePageRenovation(projectId, pageId)`
- `getTask(projectId, taskId)`

但还不完整：

1. `createRenovationProject()` 只支持 `file`
2. 文件生成没有统一的一站式前端 API 调用封装
3. 文件生成与翻新的任务轮询逻辑还没真正进入 store 主流程

### 6.3 Store

文件：`teacher-platform/src/stores/ppt.js`

当前已有：

- 项目基础信息
- 页面数据
- 普通大纲生成流程
- 参考文件上传 / parse 的基础封装

但还缺：

- 文件生成任务态
- 翻新任务态
- 失败页信息
- 任务轮询停止与恢复
- 基于项目类型的阶段恢复逻辑

### 6.4 Preview 页面

文件：`teacher-platform/src/views/ppt/PptPreview.vue`

当前已经有：

- 翻新单页再生成按钮
- `handleRenovateCurrentPage()`

这是很好的基础，但还没有完整接上项目级翻新状态和失败页提示。

## 7. 前端产品流程

## 7.1 文件生成流程

### 路径 A：仅上传文件

用户操作：

1. 首页选择 `文件生成`
2. 上传单个文件
3. 点击“下一步”

前端行为：

1. 调用文件生成后端接口
2. 获取 `project_id + task_id`
3. 轮询任务
4. 任务完成后拉取项目与页面
5. 进入 `outline`

### 路径 B：仅粘贴文本

用户操作：

1. 首页选择 `文件生成`
2. 不上传文件，只粘贴文本
3. 点击“下一步”

前端行为：

1. 调用文件生成后端接口（仅传文本）
2. 获取 `project_id + task_id`
3. 轮询任务
4. 任务完成后拉取项目与页面
5. 进入 `outline`

### 路径 C：文件 + 文本

用户操作：

1. 首页选择 `文件生成`
2. 上传单个文件
3. 补充文本说明
4. 点击“下一步”

前端行为：

1. 调用文件生成后端接口（同时传文件和文本）
2. 获取 `project_id + task_id`
3. 轮询任务
4. 任务完成后拉取项目与页面
5. 进入 `outline`

## 7.2 PPT 翻新流程

用户操作：

1. 首页选择 `PPT 翻新`
2. 上传 `pdf/ppt/pptx`
3. 点击“下一步”

前端行为：

1. 调用翻新后端接口
2. 获取 `project_id + task_id`
3. 轮询任务
4. 项目创建后先进入 `outline`
5. 页面逐步显示翻新解析结果
6. 若有失败页，用户可在预览页逐页重试

## 8. API 层需求

文件：`teacher-platform/src/api/ppt.js`

## 8.1 文件生成 API

需要新增或整理一个统一的文件生成接口封装。

建议函数签名：

```js
createFileGenerationProject({
  file,
  sourceText,
  title,
  theme,
  templateStyle,
  settings
})
```

说明：

- `file` 可选
- `sourceText` 可选
- 两者至少一个必填
- 用 `FormData` 提交

如果后端采用的是：

- `POST /api/v1/ppt/projects/file-generation`

则前端直接调用这个接口。

## 8.2 翻新 API

需要把当前：

```js
createRenovationProject(file)
```

改为支持：

- `file`
- `keep_layout`
- `template_style`
- `language`

建议签名：

```js
createRenovationProject({
  file,
  keepLayout,
  templateStyle,
  language
})
```

## 8.3 任务查询 API

继续复用：

- `getTask(projectId, taskId)`
- `getTasks(projectId)`

不要求改成 SSE。

## 9. Store 需求

文件：`teacher-platform/src/stores/ppt.js`

## 9.1 建议新增状态

建议最小新增：

- `fileGenerationTaskId`
- `fileGenerationTaskStatus`
- `fileGenerationTaskResult`
- `fileGenerationPolling`

- `renovationTaskId`
- `renovationTaskStatus`
- `renovationTaskResult`
- `renovationPolling`
- `renovationFailedPages`

也可以抽象成更通用的：

- `activeTaskId`
- `activeTaskType`
- `activeTaskStatus`
- `activeTaskResult`
- `activeTaskPolling`

但不强制抽象，遵循“够用即可”。

## 9.2 建议新增 action

### 文件生成

- `createFileGenerationProject(payload)`
- `pollFileGenerationTask(projectId, taskId)`
- `stopFileGenerationPolling()`

### 翻新

- `createRenovationProject(payload)`
- `pollRenovationTask(projectId, taskId)`
- `stopRenovationPolling()`
- `syncRenovationTaskResult(task)`

## 9.3 通用行为要求

1. 创建任务成功后，写入：
   - `projectId`
   - `projectStatus`
   - `creationType`
   - 对应任务 ID
2. 轮询任务时：
   - 调用 `getTask(projectId, taskId)`
   - 更新任务状态
   - 任务完成后重新拉取项目和页面
3. 离开项目、切换项目、重置 workspace 时：
   - 停止所有相关轮询

## 10. Home 页面需求

文件：`teacher-platform/src/views/ppt/PptHome.vue`

## 10.1 文件生成模式

### 目标

在 `creationType === 'file'` 时，不再走普通 `createProject(data)`，而是走真实文件生成创建流程。

### 行为要求

1. `file` 模式下支持：
   - 上传单文件
   - 或只粘贴文本
   - 或两者同时存在
2. 点击“下一步”时：
   - 文件和文本都为空时，提示用户
   - 至少有一个输入时，调用文件生成创建流程
3. 创建成功后：
   - 进入 `outline`
   - 启动文件生成任务轮询

### 输入要求

第一版前端上传文件类型限制为：

- `.pdf`
- `.doc`
- `.docx`

## 10.2 PPT 翻新模式

### 目标

在 `creationType === 'renovation'` 时，真正调用翻新创建接口。

### 行为要求

1. 必须上传文件
2. 支持：
   - `.pdf`
   - `.ppt`
   - `.pptx`
3. 点击“下一步”时：
   - 未上传文件则提示
   - 上传后调用翻新创建流程
4. 创建成功后：
   - 进入 `outline`
   - 启动翻新任务轮询

## 10.3 现有交互复用

Home 页应继续复用：

- 现有 mode tab
- 现有模板 / 风格 UI
- 现有 textarea
- 现有参考文件展示区域

不要求重做首页 UI。

## 11. 页面状态映射需求

文件：`teacher-platform/src/stores/ppt.js`

前端页面对象需要能表达以下状态：

### 文件生成页

- `pending`
- `completed`
- `failed`

### 翻新页

- `renovationStatus`
- `renovationError`

要求：

1. 不要再简单靠 `description ? completed : pending` 处理所有项目。
2. 对不同 `creationType` 要有不同状态映射逻辑。

## 12. Outline 页面需求

文件：`teacher-platform/src/views/ppt/PptOutline.vue`

### 文件生成

1. 文件生成任务完成后，大纲页应能直接显示自动生成的页面骨架。
2. 如果文件生成失败，应显示项目级失败提示，而不是空白页。

### 翻新

1. 显示翻新页状态：
   - 已完成
   - 待解析
   - 失败
2. 失败页要有明显提示。

## 13. Description 页面需求

文件：`teacher-platform/src/views/ppt/PptDescription.vue`

### 文件生成

1. 文件生成成功后，Description 页应能正常进入后续描述编辑流程。
2. 如果文件生成任务尚未完成，不应误导用户为“描述已完成”。

### 翻新

1. 已完成页正常显示 description
2. 失败页显示失败提示
3. pending 页显示解析中 / 待解析

## 14. Preview 页面需求

文件：`teacher-platform/src/views/ppt/PptPreview.vue`

### 文件生成

1. 文件生成成功后，Preview 页继续复用现有图片生成、预览、导出逻辑。
2. 本次不要求文件生成额外新增专属 preview 交互。

### 翻新

1. 保留现有 `handleRenovateCurrentPage()`
2. 单页重试成功后：
   - 重新 `fetchPages(projectId)`
   - 同步当前页数据
3. 单页重试失败时提示错误
4. 缩略图区域应能识别失败页
5. 若项目有失败页，可在顶部显示“部分页面解析失败，可逐页重试”

## 15. 历史项目恢复需求

文件：`teacher-platform/src/views/ppt/PptHistory.vue`

要求：

1. 历史中的 `file` 项目重新进入时，能正常恢复到：
   - outline / description / preview 的合理阶段
2. 历史中的 `renovation` 项目重新进入时，能继续恢复：
   - 页面骨架
   - 失败页信息
   - 必要时继续轮询任务

注意：

- 不要求这次重做历史页 UI 文案体系
- 但不能把 file / renovation 项目错误恢复成 dialog 项目

## 16. 阶段跳转规则

文件：`teacher-platform/src/views/ppt/PptIndex.vue`、`teacher-platform/src/stores/ppt.js`

建议规则：

### 文件生成

- 创建成功后进入 `outline`
- 任务完成后可继续流转到 `description` / `preview`

### 翻新

- 创建成功后进入 `outline`
- 页面数据逐步到位
- 用户后续正常进入 `description` / `preview`

原则：

- 不新增新的 phase
- 继续复用现有：
  - `home`
  - `dialog`
  - `outline`
  - `description`
  - `preview`

## 17. 提示文案要求

### 17.1 文件生成

- 文件和文本都为空：提示“请上传文档或粘贴文本内容”
- 文件类型错误：显示后端错误
- 文件生成处理中：提示“正在解析文档并生成大纲，请稍候”
- 文件生成失败：提示“文件生成失败，请检查文件内容后重试”

### 17.2 翻新

- 未上传文件：提示“请先上传 PDF 或 PPTX 文件”
- 翻新处理中：提示“正在解析旧 PPT，请稍候”
- 部分成功：提示“部分页面解析失败，可在预览页逐页重试”
- 全部失败：提示“翻新解析失败，请重新上传或检查文件内容”

### 17.3 单页重试

- 成功：提示“该页已重新解析完成”
- 失败：提示“该页重试失败：xxx”

## 18. 非功能要求

1. 保持现有 UI 风格
2. 直接复用现有页面结构
3. 不引入复杂新架构
4. 不要求改成 SSE
5. 轮询间隔保持简单，如 2s
6. 普通 `dialog` 流程不能被破坏
7. 现有预览页图片生成、导出、素材逻辑不能被破坏

## 19. 验收标准

满足以下条件才算完成：

### 文件生成

1. 首页选择 `文件生成` 时，可以：
   - 只上传文件
   - 只输入文本
   - 文件 + 文本结合
2. 点击“下一步”后，能真正调用文件生成后端接口
3. 任务完成后，自动进入可编辑大纲页
4. 项目重新打开时，文件生成项目能正常恢复

### PPT 翻新

1. 首页选择 `PPT 翻新` 时，点击“下一步”会真正上传文件并调用翻新接口
2. 任务状态会轮询
3. 大纲页、描述页、预览页状态会更新
4. 失败页可识别、可重试
5. 历史项目恢复正常

### 通用

1. 普通 `dialog` 项目流程不受影响
2. 不需要额外新建两套前端系统

## 20. 建议实施顺序

1. 改 `teacher-platform/src/api/ppt.js`
2. 改 `teacher-platform/src/stores/ppt.js`
3. 改 `teacher-platform/src/views/ppt/PptHome.vue`
4. 改 `teacher-platform/src/views/ppt/PptOutline.vue`
5. 改 `teacher-platform/src/views/ppt/PptDescription.vue`
6. 改 `teacher-platform/src/views/ppt/PptPreview.vue`
7. 最后检查 `teacher-platform/src/views/ppt/PptHistory.vue` 和 `PptIndex.vue`

## 21.  Claude Code 的提示词


---

你现在要在 `D:\\Develop\\Project\\AIsystem` 中实现 **PPT 文件生成 + PPT 翻新前端适配**。

后端现状：

- 文件生成后端已经完成
- PPT 翻新后端已经完成

现在需要把前端真正接起来，但要求：

- 不重做整套 PPT 前端
- 不新增复杂前端架构
- 保持现有 UI 风格
- 只做最小必要改动，让功能跑通

### 目标

实现两个真正可用的前端流程：

1. 文件生成
   - 支持仅上传单文件
   - 支持仅输入文本
   - 支持文件 + 文本组合
   - 调后端自动生成大纲
   - 成功后直接进入可编辑大纲页

2. PPT 翻新
   - 支持上传 pdf/ppt/pptx
   - 调后端翻新接口
   - 自动轮询任务
   - 大纲页 / 描述页 / 预览页识别翻新状态
   - 失败页可在预览页逐页重试

### 需要重点改的文件

- `teacher-platform/src/api/ppt.js`
- `teacher-platform/src/stores/ppt.js`
- `teacher-platform/src/views/ppt/PptHome.vue`
- `teacher-platform/src/views/ppt/PptOutline.vue`
- `teacher-platform/src/views/ppt/PptDescription.vue`
- `teacher-platform/src/views/ppt/PptPreview.vue`
- `teacher-platform/src/views/ppt/PptHistory.vue`
- `teacher-platform/src/views/ppt/PptIndex.vue`

### Home 页要求

#### 文件生成模式

- 不再走普通 `createProject(data)`
- 支持：
  - 单文件
  - 纯文本
  - 文件 + 文本
- 点击下一步后调用文件生成后端接口
- 创建成功后进入 `outline`

#### 翻新模式

- 不再走普通 `createProject(data)`
- 必须上传文件
- 点击下一步后调用翻新后端接口
- 创建成功后进入 `outline`

### store 要求

请在现有 `ppt store` 基础上增加最小必要的任务状态管理：

- 文件生成任务状态
- 翻新任务状态
- 失败页结果
- 轮询开始 / 停止

### 页面要求

#### PptOutline.vue / PptDescription.vue

- 能识别 file 和 renovation 项目的不同状态
- 失败页不能被误判成普通空白页或待生成页

#### PptPreview.vue

- 保留现有翻新单页重试
- 重试成功后重新拉取页面
- 对失败页给出明确提示

### 验收要求

请确保：

1. 文件生成入口真实可用
2. 翻新入口真实可用
3. 两种任务都会轮询
4. 页面状态会更新
5. 失败页可识别、可重试
6. 普通 dialog 流程不受影响

请直接修改代码，不要只给方案。

---
