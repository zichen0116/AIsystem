# 3D 知识图谱视觉效果优化 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将当前 3D 知识图谱从"默认 graph 可视化"提升到"宇宙星图"视觉层级，实现多层发光节点、聚类质心边捆绑、宇宙色系、多层星空、力布局调优，并修复已知 bug。

**Architecture:** 仅修改 `useKnowledgeGraph.js` composable 的渲染和力参数配置。关键设计变更：节点从单层 Sprite 改为 Group(Mesh+2xSprite) 三层结构；高亮/缩放通过 `node.__threeObj.userData` 就地修改材质属性替代全量重建；边采用两阶段渲染（力模拟期间基础曲线，模拟稳定后计算聚类质心精确 curvature）。不新增文件，不改变 API surface。

**Tech Stack:** 3d-force-graph ^1.79.1, Three.js ^0.183.2, three-spritetext ^1.10.0, d3-force-3d (transitive dep for forceCollide)

**Spec:** `docs/superpowers/specs/2026-03-24-3d-graph-visual-optimization-design.md`

---

## 文件结构

| 文件 | 职责 | 操作 |
|------|------|------|
| `teacher-platform/src/composables/useKnowledgeGraph.js` | 图谱全部渲染逻辑、力布局、交互 | 修改 |

其他文件（`LessonPrepKnowledge.vue`、`GraphConsole.vue`、`FilterPopover.vue`、`SearchPopover.vue`）不需要任何修改 —— composable 的返回接口保持不变。

---

### Task 1: Imports + 宇宙色系 + 节点尺寸辅助函数

**Files:**
- Modify: `teacher-platform/src/composables/useKnowledgeGraph.js:1-74`

本 task 替换 imports、颜色系统和新增共享辅助函数，为后续 task 奠基。

- [ ] **Step 0: 确保 `d3-force-3d` 可用**

`d3-force-3d` 是 `3d-force-graph` 的传递依赖，npm 平铺 `node_modules` 时通常可直接 import。先验证，若失败则显式安装：

```bash
cd teacher-platform && node -e "require.resolve('d3-force-3d')" 2>&1 || npm install d3-force-3d
```

- [ ] **Step 1: 替换 imports（行 1-15）**

替换文件头部 imports，新增 `Group`、`Mesh`、`MeshBasicMaterial`、`SphereGeometry`、`FogExp2`、`Vector3`，以及 `forceCollide` 来自 `d3-force-3d`：

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
  Vector3,
} from 'three'
import { UnrealBloomPass } from 'three/examples/jsm/postprocessing/UnrealBloomPass.js'
```

- [ ] **Step 2: 替换颜色系统（行 17-29）**

删除 `COLOR_POOL` 数组和 `hashCategory()` 函数，替换为宇宙色调色板 + hash 分配 + 手工覆盖三层结构：

```js
// ── 宇宙色系 ──────────────────────────────────────────────────────
const COSMIC_PALETTE = [
  '#6ea8fe', '#b490f0', '#50c8b0', '#7888cc',
  '#c07090', '#60b880', '#8899aa', '#5c8abf',
]

const CATEGORY_OVERRIDE = {
  '文学领袖': '#f0c060',
}

function getCategoryColor(category) {
  if (!category) return COSMIC_PALETTE[0]
  if (CATEGORY_OVERRIDE[category]) return CATEGORY_OVERRIDE[category]
  let hash = 0
  for (let i = 0; i < category.length; i++)
    hash = category.charCodeAt(i) + ((hash << 5) - hash)
  return COSMIC_PALETTE[Math.abs(hash) % COSMIC_PALETTE.length]
}
```

- [ ] **Step 3: 新增节点尺寸常量和辅助函数**

在 `createGlowTexture()` 函数定义之后（约行 46 后），添加：

```js
// ── 节点尺寸常量 ──────────────────────────────────────────────────
const MAX_VAL = 12
const LABEL_VAL_THRESHOLD = 5

function getNodeCoreSize(node) {
  return 1.0 + Math.pow((node.val || 1) / MAX_VAL, 0.6) * 5.0
}
```

- [ ] **Step 4: 清理 composable 内部旧颜色逻辑，新增 nodeMap**

删除 composable 内部的 `categoryColorMap` 对象和旧 `getCategoryColor` 函数（约行 66-74）。

在 composable 变量区（`let graph = null` 附近），添加：

```js
  let nodeMap = {}
```

- [ ] **Step 5: 验证构建**

```bash
cd teacher-platform && npx vite build 2>&1 | tail -5
```

Expected: 构建成功（`✓ built in`）。新 imports 中未使用的类型不会导致构建失败。

- [ ] **Step 6: 提交**

```bash
git add src/composables/useKnowledgeGraph.js
git commit -m "refactor(knowledge-graph): replace color pool with cosmic palette and add node size helpers"
```

---

### Task 2: 多层发光节点

**Files:**
- Modify: `teacher-platform/src/composables/useKnowledgeGraph.js` — `createNodeObject()`, `createNodeLabel()`, `initGraph()` 中 `nodeThreeObject`

- [ ] **Step 1: 新增共享球体几何体**

在 `const glowTexture = createGlowTexture()` 之后添加：

```js
  const coreGeometry = new SphereGeometry(1, 16, 12)
```

- [ ] **Step 2: 重写 `createNodeObject()`（约行 110-127）**

返回 Group 包含三层（核心球 + 内层光晕 + 外层光环），并在 `group.userData` 存储引用以供后续对象复用：

```js
  function createNodeObject(node) {
    const group = new Group()
    const baseColor = getCategoryColor(node.category)
    const threeColor = new Color(baseColor)
    const val = node.val || 1
    const coreSize = getNodeCoreSize(node)
    const brightness = 0.4 + 0.6 * Math.pow(val / MAX_VAL, 0.3)

    // Layer 1: 实心核心球
    const coreMat = new MeshBasicMaterial({
      color: threeColor.clone().lerp(new Color('#ffffff'), 0.5),
      transparent: true,
      opacity: 0.95 * brightness,
    })
    const core = new Mesh(coreGeometry, coreMat)
    core.scale.setScalar(coreSize * 0.3)
    group.add(core)

    // Layer 2: 内层光晕
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

    // Layer 3: 外层光环
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

    group.userData = { core, innerGlow, outerHalo, label: null }
    return group
  }
```

- [ ] **Step 3: 更新 `createNodeLabel()`（约行 130-139）**

标签颜色改为 `#aabbcc`（亮度 ≈ 0.58，低于 bloom threshold 0.65），使用 `LABEL_VAL_THRESHOLD` 常量：

```js
  function createNodeLabel(node) {
    if ((node.val || 0) < LABEL_VAL_THRESHOLD) return null
    const label = new SpriteText(node.name)
    label.color = '#aabbcc'
    label.textHeight = 2.0
    label.fontFace = 'sans-serif'
    label.backgroundColor = false
    label.padding = 0
    return label
  }
```

- [ ] **Step 4: 更新 `initGraph()` 中的初始 `nodeThreeObject`（约行 356-364）**

使用 `getNodeCoreSize` 定位标签，并将标签引用存入 `group.userData.label`：

```js
      .nodeThreeObject(node => {
        const group = createNodeObject(node)
        const label = createNodeLabel(node)
        if (label) {
          label.position.y = getNodeCoreSize(node) * 1.5 + 2
          group.add(label)
          group.userData.label = label
        }
        return group
      })
```

- [ ] **Step 5: 验证构建**

```bash
cd teacher-platform && npx vite build 2>&1 | tail -5
```

Expected: 构建成功。注意此时 `applyHighlight` 和 `checkZoomLevel` 仍使用旧的重建模式，运行时高亮/缩放行为可能不完美，Task 3 修复。

- [ ] **Step 6: 提交**

```bash
git add src/composables/useKnowledgeGraph.js
git commit -m "feat(knowledge-graph): multi-layer glow nodes with Group + Mesh core + Sprite halos"
```

---

### Task 3: 对象复用 — applyHighlight + checkZoomLevel

**Files:**
- Modify: `teacher-platform/src/composables/useKnowledgeGraph.js` — `applyHighlight()`, `checkZoomLevel()`

关键性能修正：不再通过 `graph.nodeThreeObject()` 全量重建节点对象，改为通过 `node.__threeObj.userData` 就地修改材质属性。

- [ ] **Step 1: 重写 `applyHighlight()`（约行 229-255）**

遍历 `graphData.value.nodes`，通过 `__threeObj.userData` 获取子对象引用，修改 opacity 和 visible：

```js
  function applyHighlight() {
    if (!graph) return
    const hasHighlight = highlightNodes.value.size > 0

    graphData.value.nodes.forEach(node => {
      const group = node.__threeObj
      if (!group?.userData) return
      const { core, innerGlow, outerHalo, label } = group.userData
      const val = node.val || 1
      const brightness = 0.4 + 0.6 * Math.pow(val / MAX_VAL, 0.3)

      if (hasHighlight && !highlightNodes.value.has(node)) {
        if (core) core.material.opacity = 0.95 * brightness * 0.05
        if (innerGlow) innerGlow.material.opacity = 0.7 * brightness * 0.05
        if (outerHalo) outerHalo.material.opacity = (0.15 + (val / MAX_VAL) * 0.2) * brightness * 0.05
        if (label) label.visible = false
      } else {
        if (core) core.material.opacity = 0.95 * brightness
        if (innerGlow) innerGlow.material.opacity = 0.7 * brightness
        if (outerHalo) outerHalo.material.opacity = (0.15 + (val / MAX_VAL) * 0.2) * brightness
        if (label) label.visible = labelVisible
      }
    })

    graph
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

注意：`linkDirectionalParticles` 调用在 Task 5 添加 link 粒子配置后才有实际效果。在此之前不会报错（3d-force-graph 会忽略未配置的属性访问器）。

- [ ] **Step 2: 重写 `checkZoomLevel()`（约行 311-329）**

不再调用 `graph.nodeThreeObject()`，改为直接修改标签 `visible`：

```js
  function checkZoomLevel() {
    if (!graph) return
    const dist = graph.camera().position.length()
    const shouldShow = dist < 600
    if (shouldShow !== labelVisible) {
      labelVisible = shouldShow
      graphData.value.nodes.forEach(node => {
        const label = node.__threeObj?.userData?.label
        if (label) label.visible = shouldShow
      })
    }
  }
```

- [ ] **Step 3: 验证构建**

```bash
cd teacher-platform && npx vite build 2>&1 | tail -5
```

Expected: 构建成功。

- [ ] **Step 4: 提交**

```bash
git add src/composables/useKnowledgeGraph.js
git commit -m "perf(knowledge-graph): object reuse for highlight and zoom via __threeObj.userData"
```

---

### Task 4: 多层星空 + 深度雾 + Bloom 调参

**Files:**
- Modify: `teacher-platform/src/composables/useKnowledgeGraph.js` — `addStarField()`, `setupBloom()`, `initGraph()` 中添加 FogExp2

- [ ] **Step 1: 重写 `addStarField()`（约行 77-96）**

抽取 `addStarLayer` 辅助函数，创建三层星空（远景密而小、近景稀而大）：

```js
  // ── 多层星空背景 ──────────────────────────────────────────────────
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

- [ ] **Step 2: 重写 `setupBloom()`（约行 99-105）**

包裹 try-catch 降级，调整参数（strength 1.5, radius 0.75, threshold 0.65）：

```js
  function setupBloom() {
    try {
      const bloomPass = new UnrealBloomPass()
      bloomPass.strength = 1.5
      bloomPass.radius = 0.75
      bloomPass.threshold = 0.65
      graph.postProcessingComposer().addPass(bloomPass)
    } catch (e) {
      console.warn('Bloom post-processing unavailable, falling back to sprite glow only')
    }
  }
```

- [ ] **Step 3: 在 `initGraph()` 中添加深度雾**

在 `setupBloom()` 调用之后、`addStarField()` 调用之前（约行 391-394 之间），添加：

```js
    // 深度雾：远处物体自然淡出
    graph.scene().fog = new FogExp2(0x050510, 0.0015)
```

- [ ] **Step 4: 验证构建**

```bash
cd teacher-platform && npx vite build 2>&1 | tail -5
```

Expected: 构建成功。

- [ ] **Step 5: 提交**

```bash
git add src/composables/useKnowledgeGraph.js
git commit -m "feat(knowledge-graph): multi-layer starfield, depth fog, and tuned bloom with fallback"
```

---

### Task 5: 曲线边 + 流动粒子（阶段一）

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
      // 边：曲线 + 低透明度 + 流动粒子（阶段一，力模拟期间）
      .linkCurvature(0.15)
      .linkWidth(0.3)
      .linkOpacity(0.08)
      .linkColor(link => {
        const src = typeof link.source === 'object' ? link.source : null
        const color = src ? getCategoryColor(src.category) : '#4466aa'
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

Expected: 构建成功。

- [ ] **Step 3: 提交**

```bash
git add src/composables/useKnowledgeGraph.js
git commit -m "feat(knowledge-graph): curved links with flowing directional particles"
```

---

### Task 6: 保守力布局调优

**Files:**
- Modify: `teacher-platform/src/composables/useKnowledgeGraph.js` — `initGraph()` 中 force 配置

- [ ] **Step 1: 更新 `initGraph()` 链式调用中的模拟参数**

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

- [ ] **Step 2: 在 `.graphData(data)` 之后添加力配置**

在 `graphData(data)` 调用之后、`setupBloom()` 之前，添加：

```js
    // ── 力布局调优 ─────────────────────────────────────────────────
    graph.d3Force('charge').strength(node => -60 - (node.val || 1) * 10).distanceMax(300)

    graph.d3Force('link')
      .distance(link => {
        const src = typeof link.source === 'object' ? link.source : null
        const tgt = typeof link.target === 'object' ? link.target : null
        if (src && tgt && src.category === tgt.category) return 35
        return 50
      })
      .strength(link => {
        const src = typeof link.source === 'object' ? link.source : null
        const tgt = typeof link.target === 'object' ? link.target : null
        if (src && tgt && src.category === tgt.category) return 0.6
        return 0.3
      })

    graph.d3Force('center').strength(0.05)

    graph.d3Force('collide', forceCollide()
      .radius(node => getNodeCoreSize(node) * 1.5 + 3)
      .strength(0.7)
    )
```

- [ ] **Step 3: 验证构建**

```bash
cd teacher-platform && npx vite build 2>&1 | tail -5
```

Expected: 构建成功。

- [ ] **Step 4: 提交**

```bash
git add src/composables/useKnowledgeGraph.js
git commit -m "feat(knowledge-graph): conservative force layout with cluster grouping and collision"
```

---

### Task 7: 聚类质心边捆绑（阶段二）

**Files:**
- Modify: `teacher-platform/src/composables/useKnowledgeGraph.js` — 新增 `computeClusterCentroids()`, `computeLinkBundling()`，修改 `initGraph()` 添加 `onEngineStop`

力模拟稳定后（`onEngineStop`），按 category 计算聚类质心，为每条边算出精确的 curvature 和 curveRotation，使同簇边向共同质心弯曲形成光束感。

- [ ] **Step 1: 新增 `computeClusterCentroids()` 函数**

在 `checkZoomLevel()` 函数之后、`handleResize()` 函数之前添加：

```js
  // ── 聚类质心边捆绑（阶段二）──────────────────────────────────────
  function computeClusterCentroids() {
    const clusters = {}
    graphData.value.nodes.forEach(node => {
      const cat = node.category || '__uncategorized'
      if (!clusters[cat]) clusters[cat] = { sum: new Vector3(), count: 0 }
      clusters[cat].sum.add(new Vector3(node.x, node.y, node.z))
      clusters[cat].count++
    })
    const centroids = {}
    for (const [cat, { sum, count }] of Object.entries(clusters)) {
      centroids[cat] = sum.divideScalar(count)
    }
    return centroids
  }
```

- [ ] **Step 2: 新增 `computeLinkBundling()` 函数**

紧接 `computeClusterCentroids()` 之后添加。对每条 link，计算中点 M 到相关质心 C 的垂直分量，得出 curvature 和 curveRotation：

```js
  function computeLinkBundling() {
    const centroids = computeClusterCentroids()

    graphData.value.links.forEach(link => {
      const src = typeof link.source === 'object' ? link.source : null
      const tgt = typeof link.target === 'object' ? link.target : null
      if (!src || !tgt) {
        link.__bundleCurvature = 0.15
        link.__bundleRotation = 0
        return
      }

      const A = new Vector3(src.x, src.y, src.z)
      const B = new Vector3(tgt.x, tgt.y, tgt.z)
      const D = new Vector3().subVectors(B, A)
      const linkLen = D.length()
      if (linkLen < 1e-6) {
        link.__bundleCurvature = 0.05
        link.__bundleRotation = 0
        return
      }
      D.normalize()

      const M = new Vector3().addVectors(A, B).multiplyScalar(0.5)

      // 取相关质心（同簇取簇心，跨簇取两簇心中点）
      const srcCat = src.category || '__uncategorized'
      const tgtCat = tgt.category || '__uncategorized'
      let C
      if (srcCat === tgtCat) {
        C = centroids[srcCat] || M.clone()
      } else {
        const c1 = centroids[srcCat] || M.clone()
        const c2 = centroids[tgtCat] || M.clone()
        C = new Vector3().addVectors(c1, c2).multiplyScalar(0.5)
      }

      // M→C 投影到 AB 的垂直平面
      const MC = new Vector3().subVectors(C, M)
      const projOnD = D.clone().multiplyScalar(MC.dot(D))
      const perpComponent = new Vector3().subVectors(MC, projOnD)
      const perpLen = perpComponent.length()

      // curvature = |垂直分量| / |AB|，clamp 到 [0.05, 0.6]
      link.__bundleCurvature = Math.max(0.05, Math.min(0.6, perpLen / linkLen))

      // curveRotation 相对于 XY 平面交线方向
      if (perpLen < 1e-6) {
        link.__bundleRotation = 0
        return
      }

      const bundleDir = perpComponent.normalize()
      const zAxis = new Vector3(0, 0, 1)
      const crossDZ = new Vector3().crossVectors(D, zAxis)

      if (crossDZ.length() < 1e-6) {
        // link 平行于 Z 轴，用 X 做参考
        link.__bundleRotation = Math.atan2(bundleDir.y, bundleDir.x)
        return
      }

      // refDir = normalize(D × Z × D)
      const refDir = new Vector3().crossVectors(crossDZ, D).normalize()
      const perpRef = new Vector3().crossVectors(D, refDir)
      link.__bundleRotation = Math.atan2(bundleDir.dot(perpRef), bundleDir.dot(refDir))
    })

    // 应用计算后的 per-link 曲率
    graph
      .linkCurvature(link => link.__bundleCurvature || 0.15)
      .linkCurveRotation(link => link.__bundleRotation || 0)
  }
```

- [ ] **Step 3: 在 `initGraph()` 中添加 `onEngineStop` 回调**

在力配置（Task 6 添加的 `graph.d3Force('collide', ...)` 之后），添加：

```js
    // 力模拟稳定后，计算精确的聚类质心边捆绑
    graph.onEngineStop(() => {
      computeLinkBundling()
    })
```

- [ ] **Step 4: 验证构建**

```bash
cd teacher-platform && npx vite build 2>&1 | tail -5
```

Expected: 构建成功。

- [ ] **Step 5: 提交**

```bash
git add src/composables/useKnowledgeGraph.js
git commit -m "feat(knowledge-graph): cluster-centroid edge bundling computed on engine stop"
```

---

### Task 8: Bug 修复 — nodeMap 可见性 + 安全销毁

**Files:**
- Modify: `teacher-platform/src/composables/useKnowledgeGraph.js` — `initGraph()`, `updateVisibility()`, `destroy()`

- [ ] **Step 1: 在 `initGraph()` 中构建 nodeMap**

在 `graphData.value = data` 之后（约行 342 后），添加：

```js
    // 构建 node lookup map（供 updateVisibility 使用）
    nodeMap = {}
    data.nodes.forEach(n => { nodeMap[n.id] = n })
```

- [ ] **Step 2: 修复 `updateVisibility()`（约行 298-307）**

替换 link.source/target 回退空字符串的不安全写法，改用 nodeMap：

```js
  function updateVisibility() {
    if (!graph) return
    graph
      .nodeVisibility(node => !hiddenCategories.value.has(node.category))
      .linkVisibility(link => {
        const srcId = typeof link.source === 'object' ? link.source.id : link.source
        const tgtId = typeof link.target === 'object' ? link.target.id : link.target
        const srcNode = nodeMap[srcId]
        const tgtNode = nodeMap[tgtId]
        if (!srcNode || !tgtNode) return false
        return !hiddenCategories.value.has(srcNode.category) && !hiddenCategories.value.has(tgtNode.category)
      })
  }
```

- [ ] **Step 3: 重写 `destroy()`（约行 424-440）**

不再仅依赖私有 `_destructor`，先通过官方 API 释放 GPU 资源，再兜底调用私有 API：

```js
  function destroy() {
    pause()
    if (containerRef.value) {
      containerRef.value.removeEventListener('mousemove', resetIdleTimer)
      containerRef.value.removeEventListener('mousedown', resetIdleTimer)
      containerRef.value.removeEventListener('wheel', resetIdleTimer)
    }
    if (graph) {
      // 释放节点 Group 子对象的 GPU 资源
      graphData.value.nodes.forEach(node => {
        const group = node.__threeObj
        if (!group) return
        group.children.forEach(child => {
          if (child.geometry) child.geometry.dispose()
          if (child.material) {
            if (child.material.map) child.material.map.dispose()
            child.material.dispose()
          }
        })
      })

      // 释放星空层
      graph.scene().children.forEach(child => {
        if (child instanceof Points) {
          child.geometry.dispose()
          child.material.dispose()
        }
      })

      // 官方 API 清理
      graph.pauseAnimation()
      try { graph.controls()?.dispose() } catch (_) {}
      try { graph.renderer()?.dispose() } catch (_) {}
      if (containerRef.value) containerRef.value.innerHTML = ''

      // 兜底私有 API（受版本约束 ^1.79.1）
      try {
        if (typeof graph._destructor === 'function') graph._destructor()
      } catch (_) {}

      graph = null
    }
    nodeMap = {}
  }
```

- [ ] **Step 4: 验证构建**

```bash
cd teacher-platform && npx vite build 2>&1 | tail -5
```

Expected: 构建成功。

- [ ] **Step 5: 提交**

```bash
git add src/composables/useKnowledgeGraph.js
git commit -m "fix(knowledge-graph): nodeMap for link visibility and safe GPU resource disposal"
```

---

### Task 9: 最终构建验证

- [ ] **Step 1: 完整生产构建**

```bash
cd teacher-platform && npx vite build
```

Expected: 构建成功，无 warning（unused imports 在 production build 中会被 tree-shake）。

- [ ] **Step 2: 视觉验收清单（需启动前后端）**

启动后端 `cd backend && python run.py`，启动前端 `cd teacher-platform && npm run dev`，打开知识图谱页面，逐项检查：

| # | 检查项 | 操作 | 预期 |
|---|--------|------|------|
| 1 | 多层发光节点 | 观察节点 | 核心球 + 内层光晕 + 外层弥散，苏轼最大最亮 |
| 2 | 节点层次 | 对比大小节点 | 叶子节点暗小，核心节点亮大 |
| 3 | 曲线边 | 观察连线 | 弧形曲线，同簇边向质心弯曲 |
| 4 | 流动粒子 | 观察边上 | 小光点沿曲线流动 |
| 5 | 宇宙色系 | 整体观感 | 蓝紫为主，金色点缀 |
| 6 | 多层星空 | 缩远观察 | 远处密而小，近处稀而大 |
| 7 | 深度雾 | 远处节点 | 自然淡出到背景色 |
| 8 | Bloom 效果 | 核心节点 | 弥散发光，文字不糊 |
| 9 | 力布局 | 整体结构 | 同派温和聚簇，不散乱 |
| 10 | 点击高亮 | 点击节点 | 关联亮，其余暗淡（无闪烁），粒子加速 |
| 11 | 点击恢复 | 点击空白 | 恢复正常 |
| 12 | Hover tooltip | 悬浮节点 | 显示名字/分类/关联数 |
| 13 | 标签筛选 | 底部按钮 | 弹出浮层，切换分类，边随节点隐藏 |
| 14 | 搜索 | 输入"苏轼" | 匹配并飞向节点 |
| 15 | 自动旋转 | 3秒不动 | 缓慢旋转 |
| 16 | FPS | 操作过程 | ≥ 30 FPS |

- [ ] **Step 3: 修复发现的问题（若有）**

- [ ] **Step 4: 最终提交（若有修复）**

```bash
git add src/composables/useKnowledgeGraph.js
git commit -m "fix(knowledge-graph): address visual issues from optimization acceptance testing"
```
