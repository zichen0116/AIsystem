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

// ── 节点尺寸常量 ──────────────────────────────────────────────────
const MAX_VAL = 12
const LABEL_VAL_THRESHOLD = 5

function getNodeCoreSize(node) {
  return 1.0 + Math.pow((node.val || 1) / MAX_VAL, 0.6) * 5.0
}

// ── 主 Composable ──────────────────────────────────────────────────
export function useKnowledgeGraph(containerRef) {
  let graph = null
  let nodeMap = {}
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
  const isRotating = shallowRef(true)

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
  const coreGeometry = new SphereGeometry(1, 16, 12)

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

  // ── 节点标签（仅大节点常显）──────────────────────────────────────
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

  // ── 自动旋转 ────────────────────────────────────────────────────
  let angle = 0
  function startAutoRotate() {
    if (autoRotating || !isRotating.value) return
    autoRotating = true
    const cam = graph.camera().position
    const distance = Math.sqrt(cam.x * cam.x + cam.z * cam.z)
    const currentY = cam.y
    angle = Math.atan2(cam.x, cam.z)
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
        const neighborId = src.id === node.id ? tgt.id : src.id
        const neighbor = graphData.value.nodes.find(n => n.id === neighborId)
        if (neighbor) newHighlightNodes.add(neighbor)
      }
    })

    highlightNodes.value = newHighlightNodes
    highlightLinks.value = newHighlightLinks
    selectedNode.value = node

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

  // ── 交互：hover tooltip ─────────────────────────────────────────
  const hoverNode = shallowRef(null)
  let hoverRaf = null

  function handleNodeHover(node) {
    if (hoverRaf) cancelAnimationFrame(hoverRaf)
    hoverRaf = requestAnimationFrame(() => {
      hoverNode.value = node || null
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
      graphData.value.nodes.forEach(node => {
        const label = node.__threeObj?.userData?.label
        if (label) label.visible = shouldShow
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
        const group = createNodeObject(node)
        const label = createNodeLabel(node)
        if (label) {
          label.position.y = getNodeCoreSize(node) * 1.5 + 2
          group.add(label)
          group.userData.label = label
        }
        return group
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
      if (typeof graph._destructor === 'function') {
        graph._destructor()
      } else {
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
