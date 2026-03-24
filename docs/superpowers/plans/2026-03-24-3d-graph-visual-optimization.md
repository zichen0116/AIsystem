# 3D 知识图谱视觉效果优化 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将当前 3D 知识图谱从"默认 graph 可视化"提升到"宇宙星图"视觉层级，实现多层发光节点、曲线流动边、宇宙色系、多层星空、力布局调优。

**Architecture:** 仅修改 `useKnowledgeGraph.js` composable 的渲染和力参数配置。不新增文件，不改变 API surface，不影响现有交互（点击、hover、搜索、筛选、旋转）。

**Tech Stack:** 3d-force-graph ^1.79.1, Three.js ^0.183.2, three-spritetext ^1.10.0, d3-force-3d (transitive dep)

**Spec:** `docs/superpowers/specs/2026-03-21-3d-knowledge-graph-design.md` + `talk.md` + `ISSUES.md`

---

## 文件结构

| 文件 | 职责 | 操作 |
|------|------|------|
| `teacher-platform/src/composables/useKnowledgeGraph.js` | 图谱全部渲染逻辑、力布局、交互 | 修改 |

其他文件（`LessonPrepKnowledge.vue`、`GraphConsole.vue`、`FilterPopover.vue`、`SearchPopover.vue`）不需要任何修改 —— composable 的返回接口保持不变。

---

### Task 1: 宇宙色系 + 辅助函数

**Files:**
- Modify: `teacher-platform/src/composables/useKnowledgeGraph.js:1-74`

本 task 替换颜色系统和新增共享辅助函数，为后续 task 奠基。

- [ ] **Step 1: 替换 imports，新增 Three.js 类型**

替换文件头部 imports（行 1-15）：

```js
import { shallowRef } from 'vue'
import ForceGraph3D from '3d-force-graph'
import SpriteText from 'three-spritetext'
import { forceCollide } from 'd3-force-3d'
import {
  BufferGeometry,
  Float32BufferAttribute,
  PointsMaterial,
  Points,
  SpriteMaterial,
  Sprite,
  CanvasTexture,
  Color,
  AdditiveBlending,
  Group,
  Mesh,
  MeshBasicMaterial,
  SphereGeometry,
  FogExp2,
} from 'three'
import { UnrealBloomPass } from 'three/examples/jsm/postprocessing/UnrealBloomPass.js'
```

- [ ] **Step 2: 替换颜色系统（行 17-29）**

删除 `COLOR_POOL` 数组和 `hashCategory()` 函数，替换为手工宇宙色映射：

```js
// ── 宇宙色系 ──────────────────────────────────────────────────────
const CATEGORY_COLORS = {
  '豪放派': '#6ea8fe',    // 亮蓝
  '婉约派': '#b490f0',    // 柔紫
  '文学领袖': '#f0c060',  // 暖金（中心人物）
  '江西诗派': '#50c8b0',  // 青绿
  '格律派': '#7888cc',    // 灰蓝
  '南唐遗韵': '#c07090',  // 暗玫瑰
  '田园诗派': '#60b880',  // 翠绿
  '隐逸派': '#8899aa',    // 冷灰
}
const COLOR_FALLBACK = '#5566aa'
```

- [ ] **Step 3: 替换 `getCategoryColor()` 和新增 `getNodeCoreSize()`（行 66-74）**

删除 `categoryColorMap` 缓存对象和旧 `getCategoryColor`，替换为：

```js
  // ── 颜色和尺寸辅助 ─────────────────────────────────────────────
  function getCategoryColor(category) {
    if (!category) return COLOR_FALLBACK
    return CATEGORY_COLORS[category] || COLOR_FALLBACK
  }

  // 节点核心尺寸：val=1 → 1.5, val=12(苏轼) → 6
  const MAX_VAL = 12
  function getNodeCoreSize(node) {
    return 1.0 + Math.pow((node.val || 1) / MAX_VAL, 0.6) * 5.0
  }
```

- [ ] **Step 4: 验证语法**

```bash
cd teacher-platform
npx vite build 2>&1 | tail -5
```

Expected: 构建成功（`✓ built in`）。

- [ ] **Step 5: 提交**

```bash
git add src/composables/useKnowledgeGraph.js
git commit -m "refactor(knowledge-graph): replace color pool with cosmic color scheme and add helpers"
```

---

### Task 2: 节点多层发光体

**Files:**
- Modify: `teacher-platform/src/composables/useKnowledgeGraph.js` — `createNodeObject()`, `createNodeLabel()`, `applyHighlight()`, `checkZoomLevel()`, `initGraph()` 中标签定位

- [ ] **Step 1: 新增共享几何体（在 `const glowTexture = createGlowTexture()` 后面）**

```js
  const coreGeometry = new SphereGeometry(1, 16, 12)
```

- [ ] **Step 2: 重写 `createNodeObject()`（行 110-127）**

```js
  function createNodeObject(node) {
    const group = new Group()
    const baseColor = getCategoryColor(node.category)
    const threeColor = new Color(baseColor)
    const val = node.val || 1
    const coreSize = getNodeCoreSize(node)

    // 亮度因子：边缘节点暗，核心节点亮
    const brightness = 0.4 + 0.6 * Math.pow(val / MAX_VAL, 0.3)

    // Layer 1: 实心核心球 — 小而亮
    const coreMat = new MeshBasicMaterial({
      color: threeColor.clone().lerp(new Color('#ffffff'), 0.5),
      transparent: true,
      opacity: 0.95 * brightness,
    })
    const core = new Mesh(coreGeometry, coreMat)
    core.scale.setScalar(coreSize * 0.3)
    group.add(core)

    // Layer 2: 内层光晕 — 紧凑，触发 bloom
    const innerMat = new SpriteMaterial({
      map: glowTexture,
      color: threeColor.clone().multiplyScalar(1.8),
      transparent: true,
      opacity: 0.7 * brightness,
      blending: AdditiveBlending,
      depthWrite: false,
    })
    const innerGlow = new Sprite(innerMat)
    innerGlow.scale.setScalar(coreSize * 1.2)
    group.add(innerGlow)

    // Layer 3: 外层光环 — 大而淡
    const outerMat = new SpriteMaterial({
      map: glowTexture,
      color: threeColor.clone().multiplyScalar(1.2),
      transparent: true,
      opacity: (0.15 + (val / MAX_VAL) * 0.2) * brightness,
      blending: AdditiveBlending,
      depthWrite: false,
    })
    const outerHalo = new Sprite(outerMat)
    outerHalo.scale.setScalar(coreSize * 3.0)
    group.add(outerHalo)

    return group
  }
```

- [ ] **Step 3: 更新 `createNodeLabel()`（行 130-139）**

```js
  function createNodeLabel(node) {
    if ((node.val || 0) < 3) return null // 阈值从5降到3，显示更多标签
    const label = new SpriteText(node.name)
    label.color = '#aabbcc'
    label.textHeight = 2.0
    label.fontFace = 'sans-serif'
    label.backgroundColor = false
    label.padding = 0
    return label
  }
```

- [ ] **Step 4: 更新所有标签定位**

在文件中所有出现 `label.position.y = Math.max(3, Math.sqrt(node.val || 1) * 3) / 2 + 2` 的地方，替换为：

```js
label.position.y = getNodeCoreSize(node) * 1.5 + 2
```

出现在以下位置：
- `applyHighlight()` 中（约行 245）
- `checkZoomLevel()` 中（约行 322）
- `initGraph()` 链式调用中（约行 360）

- [ ] **Step 5: 更新 `applyHighlight()` 适配 Group 结构（行 229-255）**

```js
  function applyHighlight() {
    if (!graph) return
    const hasHighlight = highlightNodes.value.size > 0

    graph
      .nodeThreeObject(node => {
        const group = createNodeObject(node)
        if (hasHighlight && !highlightNodes.value.has(node)) {
          // 暗淡 Group 内所有子对象
          group.children.forEach(child => {
            if (child.material) child.material.opacity *= 0.05
          })
        }
        if (labelVisible) {
          const label = createNodeLabel(node)
          if (label) {
            if (hasHighlight && !highlightNodes.value.has(node)) {
              label.material.opacity = 0.05
            }
            label.position.y = getNodeCoreSize(node) * 1.5 + 2
            group.add(label)
          }
        }
        return group
      })
      .linkOpacity(link => {
        if (!hasHighlight) return 0.08
        return highlightLinks.value.has(link) ? 0.5 : 0.01
      })
      .linkDirectionalParticles(link => {
        if (!hasHighlight) return 2
        return highlightLinks.value.has(link) ? 4 : 0
      })
  }
```

- [ ] **Step 6: 更新 `checkZoomLevel()`（行 310-329）— 适配 Group**

```js
  function checkZoomLevel() {
    if (!graph) return
    const dist = graph.camera().position.length()
    const shouldShow = dist < 600
    if (shouldShow !== labelVisible) {
      labelVisible = shouldShow
      graph.nodeThreeObject(node => {
        const group = createNodeObject(node)
        if (labelVisible) {
          const label = createNodeLabel(node)
          if (label) {
            label.position.y = getNodeCoreSize(node) * 1.5 + 2
            group.add(label)
          }
        }
        return group
      })
    }
  }
```

- [ ] **Step 7: 更新 `initGraph()` 中初始 `nodeThreeObject`（约行 356-364）**

```js
      .nodeThreeObject(node => {
        const group = createNodeObject(node)
        const label = createNodeLabel(node)
        if (label) {
          label.position.y = getNodeCoreSize(node) * 1.5 + 2
          group.add(label)
        }
        return group
      })
```

- [ ] **Step 8: 验证构建**

```bash
cd teacher-platform && npx vite build 2>&1 | tail -5
```

- [ ] **Step 9: 提交**

```bash
git add src/composables/useKnowledgeGraph.js
git commit -m "feat(knowledge-graph): multi-layer glow nodes with Group + Mesh core + Sprite halos"
```

---

### Task 3: 曲线边 + 流动粒子

**Files:**
- Modify: `teacher-platform/src/composables/useKnowledgeGraph.js` — `initGraph()` 中的 link 配置链

- [ ] **Step 1: 替换 `initGraph()` 中的边配置（约行 373-379）**

将：
```js
      .linkWidth(0)
      .linkOpacity(0.12)
      .linkColor(link => {
        const src = typeof link.source === 'object' ? link.source : null
        return src ? getCategoryColor(src.category) : '#ffffff'
      })
```

替换为：
```js
      // 边：曲线 + 低透明度 + 流动粒子
      .linkCurvature(0.25)
      .linkCurveRotation(link => {
        // 用字符 hash 避免对非数字 ID 返回 NaN
        const srcId = typeof link.source === 'object' ? link.source.id : link.source
        const tgtId = typeof link.target === 'object' ? link.target.id : link.target
        const hash = (srcId + tgtId).split('').reduce((a, c) => a + c.charCodeAt(0), 0)
        return hash * 0.5
      })
      .linkWidth(0.3)
      .linkOpacity(0.08)
      .linkColor(link => {
        const src = typeof link.source === 'object' ? link.source : null
        const color = src ? getCategoryColor(src.category) : '#4466aa'
        // 混入蓝灰色，减少分类色刺眼感
        return new Color(color).lerp(new Color('#1a1a3e'), 0.6).getStyle()
      })
      .linkDirectionalParticles(2)
      .linkDirectionalParticleSpeed(0.004)
      .linkDirectionalParticleWidth(1.2)
      .linkDirectionalParticleColor(link => {
        const src = typeof link.source === 'object' ? link.source : null
        return src ? getCategoryColor(src.category) : '#4466aa'
      })
```

- [ ] **Step 2: 验证构建**

```bash
cd teacher-platform && npx vite build 2>&1 | tail -5
```

- [ ] **Step 3: 提交**

```bash
git add src/composables/useKnowledgeGraph.js
git commit -m "feat(knowledge-graph): curved links with flowing directional particles"
```

---

### Task 4: 多层星空 + 深度雾 + Bloom 调参

**Files:**
- Modify: `teacher-platform/src/composables/useKnowledgeGraph.js` — `addStarField()`, `setupBloom()`, `initGraph()`

- [ ] **Step 1: 重写 `addStarField()`（行 77-96）**

```js
  // ── 多层星空背景 ──────────────────────────────────────────────
  function addStarLayer(scene, { count, spread, size, opacity }) {
    const positions = new Float32Array(count * 3)
    for (let i = 0; i < count * 3; i += 3) {
      positions[i] = (Math.random() - 0.5) * spread
      positions[i + 1] = (Math.random() - 0.5) * spread
      positions[i + 2] = (Math.random() - 0.5) * spread
    }
    const geometry = new BufferGeometry()
    geometry.setAttribute('position', new Float32BufferAttribute(positions, 3))
    const material = new PointsMaterial({
      color: 0xccddff,
      size,
      transparent: true,
      opacity,
      blending: AdditiveBlending,
      depthWrite: false,
      sizeAttenuation: true,
    })
    scene.add(new Points(geometry, material))
  }

  function addStarField() {
    const scene = graph.scene()
    addStarLayer(scene, { count: 3000, spread: 6000, size: 0.8, opacity: 0.3 })
    addStarLayer(scene, { count: 800, spread: 3000, size: 2.0, opacity: 0.5 })
    addStarLayer(scene, { count: 150, spread: 1500, size: 4.0, opacity: 0.8 })
  }
```

- [ ] **Step 2: 调整 `setupBloom()`（行 99-105）**

```js
  function setupBloom() {
    const bloomPass = new UnrealBloomPass()
    bloomPass.strength = 1.5     // was 2 — 稍降，让核心节点更突出
    bloomPass.radius = 0.75      // was 0.5 — 更宽的弥散
    bloomPass.threshold = 0.6    // was 0.8 — 降低阈值，更多层发光
    graph.postProcessingComposer().addPass(bloomPass)
  }
```

- [ ] **Step 3: 在 `initGraph()` 的 `setupBloom()` 后添加深度雾**

在 `setupBloom()` 调用之后，`addStarField()` 调用之前，添加：

```js
    // 深度雾：远处物体自然淡出
    graph.scene().fog = new FogExp2(0x050510, 0.0015)
```

- [ ] **Step 4: 验证构建**

```bash
cd teacher-platform && npx vite build 2>&1 | tail -5
```

- [ ] **Step 5: 提交**

```bash
git add src/composables/useKnowledgeGraph.js
git commit -m "feat(knowledge-graph): multi-layer starfield, depth fog, and tuned bloom"
```

---

### Task 5: 力布局调优

**Files:**
- Modify: `teacher-platform/src/composables/useKnowledgeGraph.js` — `initGraph()` 中 force 配置

- [ ] **Step 1: 在 `initGraph()` 链式调用中调整参数**

将：
```js
      .cooldownTime(5000)
      .graphData(data)
```

替换为：
```js
      .d3AlphaDecay(0.02)
      .d3VelocityDecay(0.3)
      .cooldownTime(8000)
      .graphData(data)
```

- [ ] **Step 2: 在 `.graphData(data)` 之后、`setupBloom()` 之前添加力配置**

```js
    // ── 力布局调优 ─────────────────────────────────────────────────
    // charge：核心节点排斥更强，占据更多空间
    graph.d3Force('charge').strength(node => -80 - (node.val || 1) * 15).distanceMax(300)

    // link：同类节点更紧凑，跨类更松散
    graph.d3Force('link')
      .distance(link => {
        const src = typeof link.source === 'object' ? link.source : null
        const tgt = typeof link.target === 'object' ? link.target : null
        if (src && tgt && src.category === tgt.category) return 30
        return 60
      })
      .strength(link => {
        const src = typeof link.source === 'object' ? link.source : null
        const tgt = typeof link.target === 'object' ? link.target : null
        if (src && tgt && src.category === tgt.category) return 0.8
        return 0.2
      })

    // center：轻微中心吸引
    graph.d3Force('center').strength(0.05)

    // collision：防止核心节点重叠
    graph.d3Force('collide', forceCollide()
      .radius(node => getNodeCoreSize(node) * 2 + 3)
      .strength(0.7)
    )
```

- [ ] **Step 3: 验证构建**

```bash
cd teacher-platform && npx vite build 2>&1 | tail -5
```

- [ ] **Step 4: 提交**

```bash
git add src/composables/useKnowledgeGraph.js
git commit -m "feat(knowledge-graph): tuned force layout with cluster grouping and collision"
```

---

### Task 6: 最终验收与修复

- [ ] **Step 1: 启动前后端**

```bash
# 终端1：后端
cd backend && python run.py

# 终端2：前端
cd teacher-platform && npm run dev
```

- [ ] **Step 2: 视觉验收清单**

| # | 检查项 | 操作 | 预期 |
|---|--------|------|------|
| 1 | 多层发光节点 | 观察节点 | 核心球 + 内层光晕 + 外层弥散，苏轼最大最亮 |
| 2 | 节点层次 | 对比大小节点 | 叶子节点暗小，核心节点亮大，差异明显 |
| 3 | 曲线边 | 观察连线 | 弧形曲线，非直线 |
| 4 | 流动粒子 | 观察边上 | 小光点沿曲线流动 |
| 5 | 宇宙色系 | 整体观感 | 蓝紫为主，金色点缀，非彩虹分类图 |
| 6 | 多层星空 | 缩远观察 | 远处密而小，近处稀而大 |
| 7 | 深度雾 | 远处节点 | 自然淡出到背景色 |
| 8 | Bloom 效果 | 核心节点 | 弥散发光，文字不糊 |
| 9 | 力布局 | 整体结构 | 同派聚簇，核心居中，不散乱 |
| 10 | 点击高亮 | 点击节点 | 关联节点/边亮，其余暗淡，粒子加速 |
| 11 | 点击恢复 | 点击空白 | 恢复正常 |
| 12 | Hover tooltip | 悬浮节点 | 显示名字/分类/关联数 |
| 13 | 标签筛选 | 底部按钮 | 弹出浮层，切换分类 |
| 14 | 搜索 | 输入"苏轼" | 匹配并飞向节点 |
| 15 | 自动旋转 | 3秒不动 | 缓慢旋转 |
| 16 | FPS | 操作过程 | ≥ 30 FPS |

- [ ] **Step 3: 修复发现的问题**

- [ ] **Step 4: 最终提交**

```bash
git add src/composables/useKnowledgeGraph.js
git commit -m "fix(knowledge-graph): address visual issues from optimization acceptance testing"
```
