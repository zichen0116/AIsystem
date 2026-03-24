# 3D 知识图谱星空可视化 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在备课页面的知识图谱子页面中实现 3D 力导向星空知识图谱，使用 3d-force-graph + UnrealBloomPass 实现恒星弥散发光效果。

**Architecture:** 完全重写 `LessonPrepKnowledge.vue`，用 3d-force-graph 渲染 3D 力导向图。后端新增 mock API 返回 50 个宋代词人节点数据。前端拆分为主视图组件 + composable（图谱逻辑）+ 底部控制台子组件，保持文件职责清晰。

**Tech Stack:** Vue 3 Composition API, 3d-force-graph, Three.js (UnrealBloomPass), three-spritetext

**Spec:** `docs/superpowers/specs/2026-03-21-3d-knowledge-graph-design.md`

---

## 文件结构

| 文件 | 职责 | 操作 |
|------|------|------|
| `teacher-platform/package.json` | 新增 3d-force-graph, three, three-spritetext 依赖 | 修改 |
| `backend/app/api/knowledge.py` | 新增 `GET /graph` mock 端点（必须在 `/{asset_id}` 之前） | 修改 |
| `teacher-platform/src/views/LessonPrepKnowledge.vue` | 主视图：图谱容器 + 生命周期管理 | 重写 |
| `teacher-platform/src/composables/useKnowledgeGraph.js` | 图谱核心逻辑：初始化、节点渲染、交互、自动旋转 | 新建 |
| `teacher-platform/src/components/knowledge-graph/GraphConsole.vue` | 底部控制台：节点网格 + 功能按钮 | 新建 |
| `teacher-platform/src/components/knowledge-graph/FilterPopover.vue` | 分类筛选浮层 | 新建 |
| `teacher-platform/src/components/knowledge-graph/SearchPopover.vue` | 搜索弹出框 | 新建 |

---

### Task 1: 安装依赖

**Files:**
- Modify: `teacher-platform/package.json`

- [ ] **Step 1: 安装 npm 包**

```bash
cd teacher-platform
npm install 3d-force-graph three three-spritetext
```

- [ ] **Step 2: 验证安装**

```bash
cat node_modules/3d-force-graph/package.json | grep version
cat node_modules/three/package.json | grep version
cat node_modules/three-spritetext/package.json | grep version
```

Expected: 三个包都有版本号输出。

- [ ] **Step 3: 提交**

```bash
git add package.json package-lock.json
git commit -m "build: add 3d-force-graph, three, three-spritetext dependencies"
```

---

### Task 2: 后端 Mock API

**Files:**
- Modify: `backend/app/api/knowledge.py` (在 `/{asset_id}` 路由之前插入)

- [ ] **Step 1: 在 knowledge.py 中添加 mock 图谱端点**

在文件中找到 `@router.get("/{asset_id}/status")` 这一行，在它**之前**插入新路由。这确保 `/graph` 不会被 `/{asset_id}` 动态路由捕获。

```python
# ── Mock 知识图谱数据 ──────────────────────────────────────────────
# 注意：CurrentUser 已在文件顶部导入（来自 app.core.auth），直接使用即可
@router.get("/graph")
async def get_knowledge_graph(
    library_id: str | None = None,
    limit: int = 50,
    current_user: CurrentUser,
):
    """返回知识图谱 mock 数据（宋代词人关系网络）"""
    poets = [
        {"id": "1", "name": "苏轼", "category": "豪放派"},
        {"id": "2", "name": "辛弃疾", "category": "豪放派"},
        {"id": "3", "name": "李清照", "category": "婉约派"},
        {"id": "4", "name": "柳永", "category": "婉约派"},
        {"id": "5", "name": "秦观", "category": "婉约派"},
        {"id": "6", "name": "欧阳修", "category": "文学领袖"},
        {"id": "7", "name": "王安石", "category": "文学领袖"},
        {"id": "8", "name": "黄庭坚", "category": "江西诗派"},
        {"id": "9", "name": "晏殊", "category": "婉约派"},
        {"id": "10", "name": "晏几道", "category": "婉约派"},
        {"id": "11", "name": "周邦彦", "category": "格律派"},
        {"id": "12", "name": "姜夔", "category": "格律派"},
        {"id": "13", "name": "吴文英", "category": "格律派"},
        {"id": "14", "name": "陆游", "category": "豪放派"},
        {"id": "15", "name": "范仲淹", "category": "文学领袖"},
        {"id": "16", "name": "司马光", "category": "文学领袖"},
        {"id": "17", "name": "梅尧臣", "category": "江西诗派"},
        {"id": "18", "name": "苏辙", "category": "豪放派"},
        {"id": "19", "name": "苏洵", "category": "文学领袖"},
        {"id": "20", "name": "曾巩", "category": "文学领袖"},
        {"id": "21", "name": "张先", "category": "婉约派"},
        {"id": "22", "name": "贺铸", "category": "婉约派"},
        {"id": "23", "name": "张元干", "category": "豪放派"},
        {"id": "24", "name": "张孝祥", "category": "豪放派"},
        {"id": "25", "name": "陈亮", "category": "豪放派"},
        {"id": "26", "name": "刘克庄", "category": "豪放派"},
        {"id": "27", "name": "史达祖", "category": "格律派"},
        {"id": "28", "name": "王沂孙", "category": "格律派"},
        {"id": "29", "name": "周密", "category": "格律派"},
        {"id": "30", "name": "蒋捷", "category": "格律派"},
        {"id": "31", "name": "文天祥", "category": "豪放派"},
        {"id": "32", "name": "岳飞", "category": "豪放派"},
        {"id": "33", "name": "李煜", "category": "南唐遗韵"},
        {"id": "34", "name": "温庭筠", "category": "南唐遗韵"},
        {"id": "35", "name": "韦庄", "category": "南唐遗韵"},
        {"id": "36", "name": "冯延巳", "category": "南唐遗韵"},
        {"id": "37", "name": "朱敦儒", "category": "婉约派"},
        {"id": "38", "name": "李之仪", "category": "婉约派"},
        {"id": "39", "name": "陈与义", "category": "江西诗派"},
        {"id": "40", "name": "吕本中", "category": "江西诗派"},
        {"id": "41", "name": "郭祥正", "category": "江西诗派"},
        {"id": "42", "name": "范成大", "category": "田园诗派"},
        {"id": "43", "name": "杨万里", "category": "田园诗派"},
        {"id": "44", "name": "刘辰翁", "category": "格律派"},
        {"id": "45", "name": "张炎", "category": "格律派"},
        {"id": "46", "name": "刘过", "category": "豪放派"},
        {"id": "47", "name": "戴复古", "category": "豪放派"},
        {"id": "48", "name": "叶梦得", "category": "豪放派"},
        {"id": "49", "name": "赵佶", "category": "南唐遗韵"},
        {"id": "50", "name": "林逋", "category": "隐逸派"},
    ]

    # 关系数据：师承、同派、同期、亲属、政治关联
    links = [
        # 苏轼的核心关系网（最多关联，作为中心大节点）
        {"source": "1", "target": "6", "relation": "受知于"},
        {"source": "1", "target": "7", "relation": "政治对立"},
        {"source": "1", "target": "8", "relation": "师生"},
        {"source": "1", "target": "5", "relation": "师生"},
        {"source": "1", "target": "18", "relation": "兄弟"},
        {"source": "1", "target": "19", "relation": "父子"},
        {"source": "1", "target": "16", "relation": "政治同僚"},
        {"source": "1", "target": "17", "relation": "文学交游"},
        {"source": "1", "target": "9", "relation": "文学传承"},
        {"source": "1", "target": "14", "relation": "风格相近"},
        {"source": "1", "target": "2", "relation": "词风继承"},
        {"source": "1", "target": "41", "relation": "文学交游"},
        # 辛弃疾关系网
        {"source": "2", "target": "25", "relation": "政治同盟"},
        {"source": "2", "target": "14", "relation": "风格相近"},
        {"source": "2", "target": "24", "relation": "词风相近"},
        {"source": "2", "target": "23", "relation": "词风相近"},
        {"source": "2", "target": "26", "relation": "师生"},
        {"source": "2", "target": "46", "relation": "交游"},
        {"source": "2", "target": "32", "relation": "精神继承"},
        # 婉约派关系
        {"source": "3", "target": "4", "relation": "同派"},
        {"source": "3", "target": "5", "relation": "同派"},
        {"source": "3", "target": "9", "relation": "词风传承"},
        {"source": "3", "target": "10", "relation": "词风相近"},
        {"source": "3", "target": "11", "relation": "词风影响"},
        {"source": "4", "target": "11", "relation": "词法影响"},
        {"source": "4", "target": "5", "relation": "同期"},
        {"source": "4", "target": "21", "relation": "词风相近"},
        {"source": "5", "target": "9", "relation": "受知于"},
        {"source": "5", "target": "22", "relation": "同期"},
        # 文学领袖关系
        {"source": "6", "target": "7", "relation": "政治对立"},
        {"source": "6", "target": "9", "relation": "文学交游"},
        {"source": "6", "target": "17", "relation": "诗文革新"},
        {"source": "6", "target": "20", "relation": "师生"},
        {"source": "6", "target": "15", "relation": "政治同僚"},
        {"source": "7", "target": "16", "relation": "政治对立"},
        {"source": "7", "target": "20", "relation": "文学交游"},
        # 格律派关系
        {"source": "11", "target": "12", "relation": "词法传承"},
        {"source": "11", "target": "13", "relation": "词法传承"},
        {"source": "12", "target": "13", "relation": "同派"},
        {"source": "12", "target": "27", "relation": "词风影响"},
        {"source": "12", "target": "28", "relation": "词风影响"},
        {"source": "12", "target": "29", "relation": "交游"},
        {"source": "12", "target": "45", "relation": "词法传承"},
        {"source": "13", "target": "27", "relation": "同派"},
        {"source": "13", "target": "44", "relation": "词风影响"},
        {"source": "28", "target": "29", "relation": "交游"},
        {"source": "29", "target": "30", "relation": "同期"},
        {"source": "45", "target": "30", "relation": "同期"},
        # 晏氏父子
        {"source": "9", "target": "10", "relation": "父子"},
        {"source": "9", "target": "6", "relation": "政治同僚"},
        # 江西诗派
        {"source": "8", "target": "39", "relation": "同派"},
        {"source": "8", "target": "40", "relation": "诗派传承"},
        {"source": "8", "target": "41", "relation": "同派"},
        {"source": "39", "target": "40", "relation": "同派"},
        # 南唐遗韵
        {"source": "33", "target": "34", "relation": "词风影响"},
        {"source": "33", "target": "35", "relation": "同期"},
        {"source": "33", "target": "36", "relation": "同期"},
        {"source": "34", "target": "35", "relation": "同期"},
        # 田园诗派
        {"source": "42", "target": "43", "relation": "同期同派"},
        {"source": "42", "target": "14", "relation": "交游"},
        # 豪放派补充
        {"source": "14", "target": "15", "relation": "精神继承"},
        {"source": "31", "target": "32", "relation": "精神相通"},
        {"source": "31", "target": "2", "relation": "精神传承"},
        {"source": "23", "target": "48", "relation": "同期"},
        {"source": "26", "target": "47", "relation": "同期"},
        # 隐逸派
        {"source": "50", "target": "17", "relation": "文学交游"},
        {"source": "50", "target": "6", "relation": "受知于"},
        # 跨派交流
        {"source": "37", "target": "3", "relation": "同期"},
        {"source": "38", "target": "1", "relation": "文学交游"},
        {"source": "49", "target": "11", "relation": "赏识"},
    ]

    # 截断节点并同步过滤边（避免边引用不存在的节点）
    selected_poets = poets[:limit]
    node_ids = {p["id"] for p in selected_poets}
    filtered_links = [
        link for link in links
        if link["source"] in node_ids and link["target"] in node_ids
    ]

    # 计算每个节点的关联数作为 val
    link_count: dict[str, int] = {}
    for link in filtered_links:
        link_count[link["source"]] = link_count.get(link["source"], 0) + 1
        link_count[link["target"]] = link_count.get(link["target"], 0) + 1

    nodes = [
        {**p, "val": link_count.get(p["id"], 1)}
        for p in selected_poets
    ]

    return {"nodes": nodes, "links": filtered_links}
```

- [ ] **Step 2: 验证路由顺序**

打开 `backend/app/api/knowledge.py`，确认 `/graph` 端点在 `/{asset_id}/status` 和 `/{asset_id}` 之前。

- [ ] **Step 3: 启动后端验证**

```bash
cd backend
python run.py
# 在另一个终端：
curl -s http://127.0.0.1:8000/api/v1/knowledge/graph -H "Authorization: Bearer <token>" | python -m json.tool | head -20
```

Expected: 返回 JSON，包含 nodes 和 links 数组。

- [ ] **Step 4: 提交**

```bash
git add backend/app/api/knowledge.py
git commit -m "feat(api): add mock knowledge graph endpoint with Song Dynasty poets data"
```

---

### Task 3: 图谱核心 Composable — 初始化 + 基础渲染

**Files:**
- Create: `teacher-platform/src/composables/useKnowledgeGraph.js`

这是最核心的文件，封装所有 3d-force-graph 逻辑。本 task 先实现基础渲染（节点 + 边 + bloom + 星空背景）。

- [ ] **Step 1: 创建 composable 文件，实现基础图谱初始化**

```js
// teacher-platform/src/composables/useKnowledgeGraph.js
import { shallowRef, onActivated, onDeactivated, onMounted, onUnmounted } from 'vue'
import ForceGraph3D from '3d-force-graph'
import SpriteText from 'three-spritetext'
import {
  BufferGeometry,
  Float32BufferAttribute,
  PointsMaterial,
  Points,
  SpriteMaterial,
  Sprite,
  TextureLoader,
  CanvasTexture,
  Color,
  AdditiveBlending,
} from 'three'
import { UnrealBloomPass } from 'three/examples/jsm/postprocessing/UnrealBloomPass.js'

// ── 颜色池 ────────────────────────────────────────────────────────
const COLOR_POOL = [
  '#60a5fa', '#a78bfa', '#34d399', '#f472b6',
  '#fb923c', '#22d3ee', '#facc15', '#f87171',
]

function hashCategory(category) {
  let hash = 0
  for (let i = 0; i < category.length; i++) {
    hash = category.charCodeAt(i) + ((hash << 5) - hash)
  }
  return COLOR_POOL[Math.abs(hash) % COLOR_POOL.length]
}

// ── 生成发光点 Sprite 纹理 ─────────────────────────────────────────
function createGlowTexture(size = 128) {
  const canvas = document.createElement('canvas')
  canvas.width = size
  canvas.height = size
  const ctx = canvas.getContext('2d')
  const center = size / 2
  const gradient = ctx.createRadialGradient(center, center, 0, center, center, center)
  gradient.addColorStop(0, 'rgba(255,255,255,1)')
  gradient.addColorStop(0.15, 'rgba(255,255,255,0.8)')
  gradient.addColorStop(0.4, 'rgba(255,255,255,0.2)')
  gradient.addColorStop(1, 'rgba(255,255,255,0)')
  ctx.fillStyle = gradient
  ctx.fillRect(0, 0, size, size)
  return new CanvasTexture(canvas)
}

// ── 主 Composable ──────────────────────────────────────────────────
export function useKnowledgeGraph(containerRef) {
  let graph = null
  let autoRotateTimer = null
  let autoRotating = false
  let mouseIdleTimeout = null
  const IDLE_DELAY = 3000
  const ROTATE_SPEED = Math.PI / 600

  // 用 shallowRef 存储需要在模板中响应的状态
  const graphData = shallowRef({ nodes: [], links: [] })
  const highlightNodes = shallowRef(new Set())
  const highlightLinks = shallowRef(new Set())
  const selectedNode = shallowRef(null)
  const categories = shallowRef([])
  const hiddenCategories = shallowRef(new Set())
  const isRotating = shallowRef(true) // 默认允许自动旋转

  // ── 类别颜色映射缓存 ───────────────────────────────────────────
  const categoryColorMap = {}
  function getCategoryColor(category) {
    if (!category) return COLOR_POOL[0]
    if (!categoryColorMap[category]) {
      categoryColorMap[category] = hashCategory(category)
    }
    return categoryColorMap[category]
  }

  // ── 星空背景粒子 ───────────────────────────────────────────────
  function addStarField() {
    const count = 2000
    const positions = new Float32Array(count * 3)
    for (let i = 0; i < count * 3; i += 3) {
      positions[i] = (Math.random() - 0.5) * 4000
      positions[i + 1] = (Math.random() - 0.5) * 4000
      positions[i + 2] = (Math.random() - 0.5) * 4000
    }
    const geometry = new BufferGeometry()
    geometry.setAttribute('position', new Float32BufferAttribute(positions, 3))
    const material = new PointsMaterial({
      color: 0xffffff,
      size: 1.5,
      transparent: true,
      opacity: 0.6,
      blending: AdditiveBlending,
    })
    const stars = new Points(geometry, material)
    graph.scene().add(stars)
  }

  // ── Bloom 后处理 ────────────────────────────────────────────────
  function setupBloom() {
    const bloomPass = new UnrealBloomPass()
    bloomPass.strength = 2
    bloomPass.radius = 0.5
    bloomPass.threshold = 0.8
    graph.postProcessingComposer().addPass(bloomPass)
  }

  // ── 节点自定义渲染（恒星发光体）──────────────────────────────────
  const glowTexture = createGlowTexture()

  function createNodeObject(node) {
    const color = getCategoryColor(node.category)
    const threeColor = new Color(color)

    // 发光点 Sprite
    const mat = new SpriteMaterial({
      map: glowTexture,
      color: threeColor.clone().multiplyScalar(1.5), // 超亮，触发 bloom
      transparent: true,
      blending: AdditiveBlending,
      depthWrite: false,
    })
    const sprite = new Sprite(mat)
    const size = Math.max(3, Math.sqrt(node.val || 1) * 3)
    sprite.scale.set(size, size, 1)

    return sprite
  }

  // ── 节点标签（仅大节点常显）──────────────────────────────────────
  function createNodeLabel(node) {
    if ((node.val || 0) < 5) return null // 小节点不常显标签
    const label = new SpriteText(node.name)
    label.color = '#cccccc' // 偏暗灰白，不触发 bloom
    label.textHeight = 2.5
    label.fontFace = 'sans-serif'
    label.backgroundColor = false
    label.padding = 0
    return label
  }

  // ── 自动旋转 ────────────────────────────────────────────────────
  let angle = 0
  function startAutoRotate() {
    if (autoRotating || !isRotating.value) return
    autoRotating = true
    const cam = graph.camera().position
    const distance = Math.sqrt(cam.x * cam.x + cam.z * cam.z) // 水平距离
    const currentY = cam.y // 保留当前 Y 值，避免跳变
    angle = Math.atan2(cam.x, cam.z) // 从当前角度开始
    ;(function rotate() {
      if (!autoRotating || !graph) return
      angle += ROTATE_SPEED
      graph.cameraPosition({
        x: distance * Math.sin(angle),
        y: currentY,
        z: distance * Math.cos(angle),
      })
      autoRotateTimer = requestAnimationFrame(rotate)
    })()
  }

  function stopAutoRotate() {
    autoRotating = false
    if (autoRotateTimer) {
      cancelAnimationFrame(autoRotateTimer)
      autoRotateTimer = null
    }
  }

  function resetIdleTimer() {
    stopAutoRotate()
    clearTimeout(mouseIdleTimeout)
    if (isRotating.value) {
      mouseIdleTimeout = setTimeout(startAutoRotate, IDLE_DELAY)
    }
  }

  function toggleRotation() {
    isRotating.value = !isRotating.value
    if (!isRotating.value) {
      stopAutoRotate()
      clearTimeout(mouseIdleTimeout)
    } else {
      resetIdleTimer()
    }
  }

  // ── 交互：点击高亮 ──────────────────────────────────────────────
  function handleNodeClick(node) {
    if (!node) return clearHighlight()
    const newHighlightNodes = new Set([node])
    const newHighlightLinks = new Set()

    graphData.value.links.forEach(link => {
      const src = typeof link.source === 'object' ? link.source : { id: link.source }
      const tgt = typeof link.target === 'object' ? link.target : { id: link.target }
      if (src.id === node.id || tgt.id === node.id) {
        newHighlightLinks.add(link)
        // 找到关联节点
        const neighborId = src.id === node.id ? tgt.id : src.id
        const neighbor = graphData.value.nodes.find(n => n.id === neighborId)
        if (neighbor) newHighlightNodes.add(neighbor)
      }
    })

    highlightNodes.value = newHighlightNodes
    highlightLinks.value = newHighlightLinks
    selectedNode.value = node

    // 应用高亮/暗淡效果
    applyHighlight()

    // 相机飞向节点
    const distance = 80
    const distRatio = 1 + distance / Math.hypot(node.x, node.y, node.z)
    graph.cameraPosition(
      { x: node.x * distRatio, y: node.y * distRatio, z: node.z * distRatio },
      node,
      2000,
    )
  }

  function clearHighlight() {
    highlightNodes.value = new Set()
    highlightLinks.value = new Set()
    selectedNode.value = null
    applyHighlight()
  }

  // ── 应用高亮/暗淡效果 ────────────────────────────────────────────
  function applyHighlight() {
    if (!graph) return
    const hasHighlight = highlightNodes.value.size > 0

    graph
      .nodeThreeObject(node => {
        const sprite = createNodeObject(node)
        // 如果有高亮且此节点不在高亮集合中，降低透明度
        if (hasHighlight && !highlightNodes.value.has(node)) {
          sprite.material.opacity = 0.05
        }
        if (labelVisible) {
          const label = createNodeLabel(node)
          if (label) {
            // 高亮时非关联节点标签也暗淡
            if (hasHighlight && !highlightNodes.value.has(node)) {
              label.material.opacity = 0.05
            }
            label.position.y = Math.max(3, Math.sqrt(node.val || 1) * 3) / 2 + 2
            sprite.add(label)
          }
        }
        return sprite
      })
      .linkOpacity(link => {
        if (!hasHighlight) return 0.12
        return highlightLinks.value.has(link) ? 0.3 : 0.02
      })
  }

  // ── 交互：hover tooltip ─────────────────────────────────────────
  const hoverNode = shallowRef(null)
  let hoverRaf = null

  function handleNodeHover(node) {
    if (hoverRaf) cancelAnimationFrame(hoverRaf)
    hoverRaf = requestAnimationFrame(() => {
      hoverNode.value = node || null
      // 更改鼠标样式
      if (containerRef.value) {
        containerRef.value.style.cursor = node ? 'pointer' : 'default'
      }
    })
  }

  // ── 聚焦节点（供控制台调用）──────────────────────────────────────
  function focusNode(node) {
    if (!node || !graph) return
    handleNodeClick(node)
  }

  // ── 搜索节点 ─────────────────────────────────────────────────────
  function searchNode(name) {
    const node = graphData.value.nodes.find(
      n => n.name.includes(name)
    )
    if (node) focusNode(node)
    return node
  }

  // ── 筛选分类 ─────────────────────────────────────────────────────
  function toggleCategory(category) {
    const newHidden = new Set(hiddenCategories.value)
    if (newHidden.has(category)) {
      newHidden.delete(category)
    } else {
      newHidden.add(category)
    }
    hiddenCategories.value = newHidden
    updateVisibility()
  }

  function updateVisibility() {
    if (!graph) return
    graph
      .nodeVisibility(node => !hiddenCategories.value.has(node.category))
      .linkVisibility(link => {
        const src = typeof link.source === 'object' ? link.source : { category: '' }
        const tgt = typeof link.target === 'object' ? link.target : { category: '' }
        return !hiddenCategories.value.has(src.category) && !hiddenCategories.value.has(tgt.category)
      })
  }

  // ── 缩放标签隐藏 ─────────────────────────────────────────────────
  let labelVisible = true
  function checkZoomLevel() {
    if (!graph) return
    const dist = graph.camera().position.length()
    const shouldShow = dist < 600
    if (shouldShow !== labelVisible) {
      labelVisible = shouldShow
      graph.nodeThreeObject(node => {
        const sprite = createNodeObject(node)
        if (labelVisible) {
          const label = createNodeLabel(node)
          if (label) {
            label.position.y = Math.max(3, Math.sqrt(node.val || 1) * 3) / 2 + 2
            sprite.add(label)
          }
        }
        return sprite
      })
    }
  }

  // ── resize 处理 ──────────────────────────────────────────────────
  function handleResize() {
    if (!graph || !containerRef.value) return
    const { clientWidth, clientHeight } = containerRef.value
    graph.width(clientWidth).height(clientHeight)
  }

  // ── 初始化 ────────────────────────────────────────────────────────
  function initGraph(data) {
    if (!containerRef.value) return

    graphData.value = data

    // 提取分类列表
    const cats = [...new Set(data.nodes.map(n => n.category).filter(Boolean))]
    categories.value = cats.map(c => ({ name: c, color: getCategoryColor(c) }))

    graph = new ForceGraph3D(containerRef.value, {
      controlType: 'orbit',
    })
      .backgroundColor('#050510')
      .showNavInfo(false)
      .width(containerRef.value.clientWidth)
      .height(containerRef.value.clientHeight)
      // 节点
      .nodeThreeObject(node => {
        const sprite = createNodeObject(node)
        const label = createNodeLabel(node)
        if (label) {
          label.position.y = Math.max(3, Math.sqrt(node.val || 1) * 3) / 2 + 2
          sprite.add(label)
        }
        return sprite
      })
      .nodeLabel(node => `
        <div style="background:rgba(10,15,30,0.9);border:1px solid rgba(100,116,139,0.3);border-radius:6px;padding:8px 12px;color:#e2e8f0;font-size:12px;font-family:sans-serif;backdrop-filter:blur(4px);">
          <div style="font-weight:600;margin-bottom:4px;">${node.name}</div>
          <div style="color:#94a3b8;font-size:11px;">分类：${node.category || '未知'}</div>
          <div style="color:#94a3b8;font-size:11px;">关联：${node.val || 0} 个节点</div>
        </div>
      `)
      .nodeOpacity(1)
      // 边
      .linkWidth(0)
      .linkOpacity(0.12)
      .linkColor(link => {
        const src = typeof link.source === 'object' ? link.source : null
        return src ? getCategoryColor(src.category) : '#ffffff'
      })
      // 交互
      .onNodeClick(handleNodeClick)
      .onNodeHover(handleNodeHover)
      .onBackgroundClick(clearHighlight)
      // 分类筛选
      .nodeVisibility(node => !hiddenCategories.value.has(node.category))
      // 力模拟
      .cooldownTime(5000)
      .graphData(data)

    // Bloom
    setupBloom()

    // 星空粒子
    addStarField()

    // 事件监听
    containerRef.value.addEventListener('mousemove', resetIdleTimer)
    containerRef.value.addEventListener('mousedown', resetIdleTimer)
    containerRef.value.addEventListener('wheel', resetIdleTimer)
    window.addEventListener('resize', handleResize)

    // 启动空闲计时器
    resetIdleTimer()

    // 缩放检查
    graph.controls().addEventListener('change', checkZoomLevel)
  }

  // ── 生命周期 ──────────────────────────────────────────────────────
  function pause() {
    if (graph) graph.pauseAnimation()
    stopAutoRotate()
    clearTimeout(mouseIdleTimeout)
    window.removeEventListener('resize', handleResize)
  }

  function resume() {
    if (graph) graph.resumeAnimation()
    window.addEventListener('resize', handleResize)
    handleResize()
    if (isRotating.value) resetIdleTimer()
  }

  function destroy() {
    pause()
    if (containerRef.value) {
      containerRef.value.removeEventListener('mousemove', resetIdleTimer)
      containerRef.value.removeEventListener('mousedown', resetIdleTimer)
      containerRef.value.removeEventListener('wheel', resetIdleTimer)
    }
    if (graph) {
      // _destructor 是 3d-force-graph 的清理方法（非公开 API，加兜底）
      if (typeof graph._destructor === 'function') {
        graph._destructor()
      } else {
        // fallback: 手动暂停 + 清空容器
        graph.pauseAnimation()
        if (containerRef.value) containerRef.value.innerHTML = ''
      }
      graph = null
    }
  }

  return {
    graphData,
    highlightNodes,
    highlightLinks,
    selectedNode,
    hoverNode,
    categories,
    hiddenCategories,
    isRotating,
    initGraph,
    pause,
    resume,
    destroy,
    focusNode,
    searchNode,
    toggleCategory,
    toggleRotation,
    getCategoryColor,
  }
}
```

- [ ] **Step 2: 验证文件语法**

```bash
cd teacher-platform
npx acorn --ecma2022 --module src/composables/useKnowledgeGraph.js > /dev/null
```

Expected: 无错误输出。

- [ ] **Step 3: 提交**

```bash
git add src/composables/useKnowledgeGraph.js
git commit -m "feat(knowledge-graph): add core composable with 3D rendering, bloom, and interactions"
```

---

### Task 4: 主视图组件 — LessonPrepKnowledge.vue 重写

**Files:**
- Rewrite: `teacher-platform/src/views/LessonPrepKnowledge.vue`

- [ ] **Step 1: 完全重写 LessonPrepKnowledge.vue**

```vue
<template>
  <div class="knowledge-graph-page">
    <!-- 3D 图谱容器 -->
    <div ref="graphContainer" class="graph-container"></div>

    <!-- Hover tooltip（小节点悬浮时显示，由 nodeLabel 处理，无需额外 DOM） -->

    <!-- 底部控制台 -->
    <GraphConsole
      :nodes="topNodes"
      :categories="kg.categories.value"
      :hidden-categories="kg.hiddenCategories.value"
      :is-rotating="kg.isRotating.value"
      :get-category-color="kg.getCategoryColor"
      @focus-node="kg.focusNode"
      @toggle-rotation="kg.toggleRotation"
      @toggle-category="kg.toggleCategory"
      @search="kg.searchNode"
    />
  </div>
</template>

<script setup>
import { ref, computed, provide, onMounted, onActivated, onDeactivated, onUnmounted } from 'vue'
import { apiRequest } from '../api/http.js'
import { useKnowledgeGraph } from '../composables/useKnowledgeGraph.js'
import GraphConsole from '../components/knowledge-graph/GraphConsole.vue'

const graphContainer = ref(null)
const kg = useKnowledgeGraph(graphContainer)

// provide 给子组件（SearchPopover 等）使用，必须在 setup 顶层同步调用
provide('graphData', kg.graphData)
provide('getCategoryColor', kg.getCategoryColor)

// Top 20 节点（按关联数降序）
const topNodes = computed(() => {
  const nodes = [...(kg.graphData.value.nodes || [])]
  nodes.sort((a, b) => (b.val || 0) - (a.val || 0))
  return nodes.slice(0, 20)
})

// 加载数据
async function loadGraphData() {
  try {
    const data = await apiRequest('/api/v1/knowledge/graph?limit=50')
    kg.initGraph(data)
  } catch (err) {
    console.error('Failed to load knowledge graph:', err)
  }
}

onMounted(() => {
  loadGraphData()
})

onActivated(() => {
  kg.resume()
})

onDeactivated(() => {
  kg.pause()
})

onUnmounted(() => {
  kg.destroy()
})
</script>

<style scoped>
.knowledge-graph-page {
  position: relative;
  width: 100%;
  height: 100%;
  background: #050510;
  overflow: hidden;
}

.graph-container {
  width: 100%;
  height: 100%;
}

/* 覆盖 3d-force-graph 默认的 tooltip 样式 */
.graph-container :deep(.graph-tooltip) {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  padding: 0 !important;
  pointer-events: none;
}
</style>
```

- [ ] **Step 2: 启动前端验证基础渲染**

```bash
cd teacher-platform
npm run dev
```

打开浏览器访问知识图谱页面，确认：
- 黑色背景 + 星空粒子可见
- 节点以发光点形式显示
- 边为纤细半透明线
- Bloom 发光效果生效
- 大节点显示名字标签
- 可以拖拽旋转

**⚠️ 此步骤为用户视觉验收点 — 等待用户反馈后再继续。**

- [ ] **Step 3: 提交**

```bash
git add src/views/LessonPrepKnowledge.vue
git commit -m "feat(knowledge-graph): rewrite view with 3D force graph and lifecycle management"
```

---

### Task 5: 底部控制台组件

**Files:**
- Create: `teacher-platform/src/components/knowledge-graph/GraphConsole.vue`

- [ ] **Step 1: 创建 GraphConsole.vue**

```vue
<template>
  <div class="graph-console">
    <!-- 节点网格 -->
    <div class="node-grid">
      <div
        v-for="node in nodes"
        :key="node.id"
        class="node-item"
        @click="$emit('focusNode', node)"
      >
        <span
          class="node-dot"
          :style="{ backgroundColor: getCategoryColor(node.category) }"
        ></span>
        <span class="node-name">{{ node.name }}</span>
        <span class="node-count">{{ node.val || 0 }}</span>
      </div>
    </div>

    <!-- 功能按钮 -->
    <div class="console-actions">
      <button class="console-btn" @click="$emit('toggleRotation')">
        {{ isRotating ? '停止旋转' : '开始旋转' }}
      </button>
      <button class="console-btn" @click="showFilter = !showFilter">
        标签筛选
      </button>
      <button class="console-btn" @click="showSearch = !showSearch">
        搜索名字
      </button>
    </div>

    <!-- 筛选浮层 -->
    <FilterPopover
      v-if="showFilter"
      :categories="categories"
      :hidden-categories="hiddenCategories"
      @toggle="handleToggleCategory"
      @close="showFilter = false"
    />

    <!-- 搜索浮层 -->
    <SearchPopover
      v-if="showSearch"
      @search="handleSearch"
      @close="showSearch = false"
    />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import FilterPopover from './FilterPopover.vue'
import SearchPopover from './SearchPopover.vue'

const props = defineProps({
  nodes: { type: Array, default: () => [] },
  categories: { type: Array, default: () => [] },
  hiddenCategories: { type: Object, default: () => new Set() },
  isRotating: { type: Boolean, default: true },
  getCategoryColor: { type: Function, required: true },
})

const emit = defineEmits(['focusNode', 'toggleRotation', 'toggleCategory', 'search'])

const showFilter = ref(false)
const showSearch = ref(false)

function handleToggleCategory(category) {
  emit('toggleCategory', category)
}

function handleSearch(name) {
  emit('search', name)
  showSearch.value = false
}
</script>

<style scoped>
.graph-console {
  position: absolute;
  bottom: 16px;
  left: 50%;
  transform: translateX(-50%);
  width: 50%;
  background: rgba(10, 15, 30, 0.85);
  border: 1px solid rgba(100, 116, 139, 0.25);
  border-radius: 12px;
  padding: 14px 18px;
  backdrop-filter: blur(8px);
  z-index: 10;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

.node-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 6px 12px;
  margin-bottom: 10px;
}

.node-item {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  padding: 3px 6px;
  border-radius: 4px;
  transition: background 0.2s;
}

.node-item:hover {
  background: rgba(51, 65, 85, 0.4);
}

.node-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

.node-name {
  color: rgba(226, 232, 240, 0.9);
  font-size: 12px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
}

.node-count {
  color: rgba(100, 116, 139, 0.7);
  font-size: 10px;
  flex-shrink: 0;
}

.console-actions {
  display: flex;
  gap: 8px;
}

.console-btn {
  flex: 1;
  background: rgba(51, 65, 85, 0.4);
  border: 1px solid rgba(71, 85, 105, 0.3);
  border-radius: 6px;
  padding: 6px 0;
  color: rgba(148, 163, 184, 0.9);
  font-size: 12px;
  cursor: pointer;
  transition: background 0.2s;
}

.console-btn:hover {
  background: rgba(71, 85, 105, 0.5);
}

/* ── 小屏适配 ── */
@media (max-width: 768px) {
  .graph-console {
    width: 90%;
    padding: 10px 12px;
  }

  .node-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  /* 小屏只显示 Top 10 */
  .node-item:nth-child(n+11) {
    display: none;
  }

  .console-btn {
    font-size: 0;
    padding: 8px;
  }

  /* 图标替代文字 */
  .console-btn::before {
    font-size: 14px;
  }

  .console-btn:nth-child(1)::before { content: '⏸'; }
  .console-btn:nth-child(2)::before { content: '🏷'; }
  .console-btn:nth-child(3)::before { content: '🔍'; }
}
</style>
```

- [ ] **Step 2: 提交**

```bash
git add src/components/knowledge-graph/GraphConsole.vue
git commit -m "feat(knowledge-graph): add bottom console component with responsive layout"
```

---

### Task 6: 筛选浮层 + 搜索浮层组件

**Files:**
- Create: `teacher-platform/src/components/knowledge-graph/FilterPopover.vue`
- Create: `teacher-platform/src/components/knowledge-graph/SearchPopover.vue`

- [ ] **Step 1: 创建 FilterPopover.vue**

```vue
<template>
  <Teleport to="body">
    <div class="filter-backdrop" @click.self="$emit('close')">
      <div class="filter-popover">
        <div class="filter-title">按分类筛选</div>
        <div class="filter-list">
          <label
            v-for="cat in categories"
            :key="cat.name"
          class="filter-item"
        >
          <input
            type="checkbox"
            :checked="!hiddenCategories.has(cat.name)"
            @change="$emit('toggle', cat.name)"
          />
          <span class="filter-dot" :style="{ backgroundColor: cat.color }"></span>
          <span class="filter-name">{{ cat.name }}</span>
        </label>
      </div>
    </div>
  </div>
  </Teleport>
</template>

<script setup>
defineProps({
  categories: { type: Array, default: () => [] },
  hiddenCategories: { type: Object, default: () => new Set() },
})

defineEmits(['toggle', 'close'])
</script>

<style scoped>
.filter-backdrop {
  position: fixed;
  inset: 0;
  z-index: 1000;
}

.filter-popover {
  position: fixed;
  bottom: 80px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(10, 15, 30, 0.92);
  border: 1px solid rgba(100, 116, 139, 0.3);
  border-radius: 10px;
  padding: 12px 16px;
  backdrop-filter: blur(12px);
  min-width: 200px;
}

.filter-title {
  color: rgba(226, 232, 240, 0.9);
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 10px;
}

.filter-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.filter-item {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 4px 6px;
  border-radius: 4px;
  transition: background 0.2s;
}

.filter-item:hover {
  background: rgba(51, 65, 85, 0.3);
}

.filter-item input[type="checkbox"] {
  accent-color: #60a5fa;
  width: 14px;
  height: 14px;
}

.filter-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.filter-name {
  color: rgba(203, 213, 225, 0.9);
  font-size: 12px;
}
</style>
```

- [ ] **Step 2: 创建 SearchPopover.vue**

```vue
<template>
  <Teleport to="body">
    <div class="search-backdrop" @click.self="$emit('close')">
      <div class="search-popover">
      <input
        ref="searchInput"
        v-model="query"
        type="text"
        placeholder="输入节点名字..."
        class="search-input"
        @keyup.enter="handleSearch"
        @input="handleInput"
      />
      <div v-if="results.length" class="search-results">
        <div
          v-for="node in results"
          :key="node.id"
          class="search-item"
          @click="selectNode(node)"
        >
          <span class="search-dot" :style="{ backgroundColor: node._color }"></span>
          <span>{{ node.name }}</span>
          <span class="search-cat">{{ node.category }}</span>
        </div>
      </div>
    </div>
  </div>
  </Teleport>
</template>

<script setup>
import { ref, onMounted, inject } from 'vue'

const props = defineProps({})
const emit = defineEmits(['search', 'close'])

const query = ref('')
const results = ref([])
const searchInput = ref(null)

// 注入 graphData 从父组件
const graphData = inject('graphData', { value: { nodes: [] } })
const getCategoryColor = inject('getCategoryColor', () => '#fff')

function handleInput() {
  if (!query.value.trim()) {
    results.value = []
    return
  }
  results.value = graphData.value.nodes
    .filter(n => n.name.includes(query.value.trim()))
    .slice(0, 8)
    .map(n => ({ ...n, _color: getCategoryColor(n.category) }))
}

function handleSearch() {
  if (query.value.trim()) {
    emit('search', query.value.trim())
  }
}

function selectNode(node) {
  emit('search', node.name)
}

onMounted(() => {
  searchInput.value?.focus()
})
</script>

<style scoped>
.search-backdrop {
  position: fixed;
  inset: 0;
  z-index: 1000;
}

.search-popover {
  position: fixed;
  bottom: 80px;
  right: 26%;
  background: rgba(10, 15, 30, 0.92);
  border: 1px solid rgba(100, 116, 139, 0.3);
  border-radius: 10px;
  padding: 10px;
  backdrop-filter: blur(12px);
  min-width: 240px;
}

.search-input {
  width: 100%;
  background: rgba(30, 41, 59, 0.6);
  border: 1px solid rgba(71, 85, 105, 0.4);
  border-radius: 6px;
  padding: 8px 12px;
  color: #e2e8f0;
  font-size: 13px;
  outline: none;
  box-sizing: border-box;
}

.search-input::placeholder {
  color: rgba(100, 116, 139, 0.6);
}

.search-input:focus {
  border-color: rgba(96, 165, 250, 0.5);
}

.search-results {
  margin-top: 8px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.search-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-radius: 4px;
  cursor: pointer;
  color: rgba(203, 213, 225, 0.9);
  font-size: 12px;
  transition: background 0.2s;
}

.search-item:hover {
  background: rgba(51, 65, 85, 0.4);
}

.search-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

.search-cat {
  margin-left: auto;
  color: rgba(100, 116, 139, 0.6);
  font-size: 11px;
}
</style>
```

- [ ] **Step 3: 确认 provide 已在 LessonPrepKnowledge.vue 中**

Task 4 的 LessonPrepKnowledge.vue 模板已在 `<script setup>` 顶层包含 `provide` 调用。无需额外修改，此步骤仅作确认。

- [ ] **Step 4: 启动验证全部功能**

```bash
cd teacher-platform
npm run dev
```

验证：
- 底部控制台显示 Top 20 节点网格
- 点击控制台节点 → 相机飞向对应节点
- "停止旋转" 按钮切换自动旋转
- "标签筛选" 弹出浮层，可按分类切换显示/隐藏
- "搜索名字" 弹出搜索框，输入名字匹配并聚焦
- 小屏（≤768px）控制台宽度变 90%，网格变 2 列

**⚠️ 此步骤为用户视觉验收点 — 等待用户反馈后再继续。**

- [ ] **Step 5: 提交**

```bash
git add src/components/knowledge-graph/FilterPopover.vue src/components/knowledge-graph/SearchPopover.vue src/views/LessonPrepKnowledge.vue
git commit -m "feat(knowledge-graph): add filter, search popovers and provide/inject for data sharing"
```

---

### Task 7: 最终验收与修复

- [ ] **Step 1: 全功能验收清单**

在浏览器中逐项测试：

| # | 功能 | 操作 | 预期 |
|---|------|------|------|
| 1 | 基础渲染 | 打开页面 | 黑色背景 + 星空粒子 + 发光节点 + 纤细边 |
| 2 | Bloom 效果 | 观察节点 | 节点发光，文字清晰不糊 |
| 3 | 大节点标签 | 观察 | 关联≥5 的节点常显名字 |
| 4 | Hover tooltip | 悬浮小节点 | 显示名字/分类/关联数 |
| 5 | 点击高亮 | 点击节点 | 关联节点/边亮，其余暗淡 |
| 6 | 点击恢复 | 点击空白 | 所有节点恢复正常 |
| 7 | 自动旋转 | 3秒不动 | 缓慢绕Y轴旋转 |
| 8 | 停止旋转 | 鼠标操作 | 立即停止 |
| 9 | 缩放隐藏 | 滚轮缩远 | 标签消失 |
| 10 | 控制台节点 | 点击控制台中的节点名 | 相机飞向该节点 |
| 11 | 标签筛选 | 点击筛选按钮 | 弹出浮层，切换分类 |
| 12 | 搜索 | 输入"苏轼" | 匹配并聚焦到苏轼节点 |
| 13 | 切 tab | 切到其他 tab 再切回 | 渲染正常恢复，无报错 |
| 14 | 小屏 | 缩窄浏览器至 <768px | 控制台 90%宽，2列网格 |
| 15 | FPS | 操作过程中 | ≥30 FPS，无卡顿 |

- [ ] **Step 2: 修复发现的问题**

根据测试结果修复 bug。

- [ ] **Step 3: 最终提交**

```bash
git add src/views/LessonPrepKnowledge.vue src/composables/useKnowledgeGraph.js src/components/knowledge-graph/
git commit -m "fix(knowledge-graph): address visual and interaction issues from acceptance testing"
```
