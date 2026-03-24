# 3D 知识图谱星空可视化 — 设计文档

## 概述

在备课页面的"知识图谱"子页面（`LessonPrepKnowledge.vue`）中，完全替换现有 2D 静态布局（包括左侧聊天面板和右侧静态画布），实现一个 3D 力导向星空知识图谱。使用 `3d-force-graph` 库，配合 Three.js UnrealBloomPass 后处理实现恒星弥散发光效果。

当前阶段只实现前端部分，后端提供 mock API 返回模拟数据。Mock API 需要 JWT 认证（与现有 `/api/v1/knowledge` 端点一致）。

## 页面布局

- 保留现有左侧导航栏（`LayoutWithNav.vue`），知识图谱为备课页面的一个 tab 子页面
- 内容区域全部用于 3D 星空图谱渲染，纯黑背景（`#050510`）
- 底部控制台浮于 3D 图谱上方，固定在页面底部

## 技术栈

| 层级 | 技术 | 用途 |
|------|------|------|
| 封装层 | `3d-force-graph` | 力导向图 API，整合 Three.js + d3-force |
| 3D 渲染 | `Three.js`（3d-force-graph 依赖） | WebGL 渲染、相机控制 |
| 物理引擎 | `d3-force-3d`（3d-force-graph 内置） | 节点引力/斥力模拟 |
| 后处理 | `UnrealBloomPass`（Three.js 扩展） | 恒星发光效果 |
| 前端框架 | Vue 3 Composition API | 组件逻辑 |

### 安装依赖

```bash
npm install 3d-force-graph three three-spritetext
```

- `three` 需要显式安装以使用 `UnrealBloomPass` 等扩展模块
- `three-spritetext` 用于节点名字标签（Sprite billboard 文字）

## Vue 3 集成注意事项

- **禁止将 Three.js/3d-force-graph 实例放入 `ref()` 或 `reactive()`**。Vue 的 Proxy 会深度递归遍历 Three.js 场景树和 WebGL 上下文，导致 `Maximum Call Stack Size Exceeded` 并卡死浏览器。
- 存放 graph 实例使用 `shallowRef()` 或 setup 顶层的普通变量 `let graph = null`。
- graphData 同理，使用 `shallowRef` 或普通对象，不需要 Vue 追踪其内部响应式。

### keep-alive 生命周期管理

当前 `LessonPrep.vue` 使用 `<keep-alive>` 包裹子组件。必须处理：

- **`onActivated`**：恢复 3D 渲染（`graph.resumeAnimation()`），重新绑定 resize 监听
- **`onDeactivated`**：暂停 3D 渲染（`graph.pauseAnimation()`），移除 resize 监听，停止自动旋转定时器
- **`onUnmounted`**：完全销毁 graph 实例（`graph._destructor()`），释放 WebGL 资源

## 节点视觉设计

### 渲染方式

使用 Three.js Sprite 而非几何体球体。每个节点为一个 Sprite，配合 UnrealBloomPass 后处理实现自然的恒星弥散发光效果。

### 大小规则

- 节点大小 = 关联边数（`node.val`）
- 关联越多，Sprite 越大，bloom 效果越强，视觉上越亮

### 大节点 vs 小节点

| 属性 | 大节点（关联 ≥ 5） | 小节点（关联 < 5） |
|------|---------------------|---------------------|
| 外观 | 较亮的发光体，有清晰圆形核心 | 仅弥散光点，无清晰边缘 |
| 名字标签 | 常显（SpriteText，billboard） | 仅 hover 时显示 tooltip |
| 光晕 | 较大，模拟亮恒星 | 较小且模糊，模拟远处暗星 |

### 颜色

- 8 色颜色池：蓝 `#60a5fa`、紫 `#a78bfa`、绿 `#34d399`、粉 `#f472b6`、橙 `#fb923c`、青 `#22d3ee`、金 `#facc15`、红 `#f87171`
- 按节点分类（`node.category`）hash 自动分配颜色
- 分类数量不固定，颜色可复用
- 同一分类始终映射到同一颜色

### Bloom 后处理参数（选择性发光策略）

Bloom 会让所有亮度超过 threshold 的像素发光。为避免白色文字被 bloom 糊掉变得不可读，采用选择性发光：

- **threshold 调高至 `0.8`**，仅高亮度像素才会触发 bloom
- **节点 Sprite 材质颜色设为超亮值**（如 `color.multiplyScalar(1.5)`），确保超过 threshold 触发发光
- **文字标签颜色设为 `#cccccc`（偏暗灰白）**，低于 threshold 不会被 bloom 影响，保持清晰可读

```js
bloomPass.strength = 2
bloomPass.radius = 0.5
bloomPass.threshold = 0.8
```

效果：**星星发光，文字不发光（清晰）**。

## 边（关系）视觉设计

- 粗细：纤细如发丝（`linkWidth: 0`，即 1px 常量线）
- 颜色：跟随源节点颜色
- 透明度：低透明度（`linkOpacity: 0.1 ~ 0.15`）避免视觉杂乱

## 背景

- 纯黑色背景（`#050510`）
- 添加星空粒子：通过 `graph.scene().add()` 添加 `THREE.Points`，随机分布的微小白色粒子模拟远处恒星

## 交互功能

### 相机控制

- 使用 `orbit` 控制模式（`controlType: 'orbit'`）
- 滚轮缩放探索全图
- 鼠标拖拽旋转视角

### 自动旋转

- 鼠标静止超过 3 秒后，绕 Y 轴缓慢水平旋转
- 检测到鼠标移动/点击/滚轮时立即停止旋转
- 旋转过程中名字标签始终面向相机（Sprite billboard 天然支持）

### 缩放标签隐藏

- 当相机距离超过阈值（缩放过小）时，隐藏所有节点名字标签
- 通过监听相机位置，动态设置 label 可见性

### Hover 提示

- 鼠标悬浮节点时显示 tooltip：节点名字、分类、关联数
- 使用 `onNodeHover` 回调 + 自定义 DOM tooltip
- hover 做 `requestAnimationFrame` 防抖

### 点击节点高亮

- 点击节点后：
  - 该节点及其所有关联节点/边保持正常亮度
  - 其余所有节点/边降低透明度至 `0.05`
  - 相机平滑移动聚焦到被点击节点
- 点击空白区域恢复所有节点/边的正常状态

### 筛选分类

- 底部"标签筛选"按钮点击后，上方弹出半透明浮层
- 浮层展示所有分类标签（带颜色圆点），点击切换该分类的显示/隐藏
- 点击浮层外部关闭

### 搜索名字

- 底部"搜索名字"按钮点击后展开输入框
- 输入文字实时模糊匹配节点名字
- 选择匹配项后相机平滑飞向该节点

## 底部控制台

### 布局

- 固定在页面最底部，水平居中
- **桌面端**：宽度占内容区域的 50%，两侧各留 25%
- **小屏适配**（≤768px）：宽度扩展至 90%，节点网格改为 2 列布局（只展示 Top 10），功能按钮改为图标形式减少空间占用
- 半透明暗色背景（`rgba(10, 15, 30, 0.85)`），极细浅色边框
- `backdrop-filter: blur(8px)` 毛玻璃效果

### 内容

- **节点网格**：4 行 5 列 = 展示 Top 20 关联数最多的节点
  - 每个节点项：左侧颜色圆点 + 节点名字（白色柔和字体） + 右侧关联数（灰色偏小字体）
  - 点击节点项 → 3D 相机平滑移动至该节点为中心

- **功能按钮**：底部一行，3 个扁长按钮
  1. **停止旋转** — 切换自动旋转开关（文字随状态变化："停止旋转"/"开始旋转"）
  2. **标签筛选** — 弹出分类筛选浮层
  3. **搜索名字** — 展开搜索输入框

### 样式

- 文字：白色柔和无衬线字体，字号偏小
- 按钮：暗色半透明背景（`rgba(51, 65, 85, 0.4)`），圆角，hover 略亮
- 整体风格：暗黑科技风终端控制台

## 模拟数据

### 数据规模

- 50 个节点（宋代词人名字）
- 多种分类（词派、时期等，具体分类不固定）
- 节点间关系随机生成，确保部分节点有 ≥5 个关联

### 后端 Mock API

- 路径：`GET /api/v1/knowledge/graph?library_id=xxx&limit=50`
- `library_id`：可选，指定知识库 ID（mock 阶段忽略，但参数预留）
- `limit`：可选，限制返回节点数（默认 50）
- **路由注册顺序**：此静态路由必须注册在 `/{asset_id}` 动态路由之前，避免被动态路由吃掉导致 422
- 返回格式：

```json
{
  "nodes": [
    { "id": "1", "name": "苏轼", "category": "豪放派", "val": 12 },
    { "id": "2", "name": "辛弃疾", "category": "豪放派", "val": 8 }
  ],
  "links": [
    { "source": "1", "target": "2", "relation": "同派词人" }
  ]
}
```

- `val` 字段 = 该节点的关联边数，用于决定节点大小

### 前端默认行为

- 页面加载时通过现有 `http.js` 封装（已配置 JWT Bearer Token）调用 mock API，禁止裸 fetch
- 一次加载全部 50 个节点

## 性能优化

- **Sprite 替代几何体**：减少 draw call
- **仅大节点常显标签**：小节点用 hover tooltip，避免 DOM/Canvas 文本过载
- **hover/筛选防抖**：`requestAnimationFrame` 节流
- **力模拟 cooldown**：5 秒后停止力计算（`cooldownTime: 5000`）
- **缩放标签隐藏**：相机过远时不渲染标签文字
- **keep-alive 暂停恢复**：切 tab 后暂停渲染释放 GPU/CPU（见上方生命周期管理）

### 基础验收指标

- 50 节点场景稳定 ≥30 FPS
- 切 tab 后 GPU/CPU 占用明显下降（pauseAnimation 生效）
- 点击空白区域恢复所有节点正常状态
- 401 时不白屏，跳转登录页

## 文件变更范围

| 文件 | 变更 |
|------|------|
| `teacher-platform/src/views/LessonPrepKnowledge.vue` | 完全重写 |
| `teacher-platform/package.json` | 新增 `3d-force-graph`、`three`、`three-spritetext` 依赖 |
| `backend/app/api/knowledge.py`（或类似） | 新增 mock API 端点 |

## 不在本次范围

- 后端真实知识图谱数据接入（仅 mock）
- Redis 缓存
- 节点聚合算法（社区发现）
- 分批加载/虚拟化（50 节点无需）
