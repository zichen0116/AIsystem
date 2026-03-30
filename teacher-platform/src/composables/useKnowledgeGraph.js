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
  '#ff6b4a', '#ff9f43', '#ffd93d', '#6ba7ff',
  '#4ecdc4', '#45b7d1', '#a78bfa', '#f472b6',
]

const CATEGORY_OVERRIDE = {
  '文学领袖': '#ff4040'
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
const LABEL_MIN_ASSOCIATIONS = 5
const LABEL_SHOW_NEAR_DIST = 130
const LABEL_SHOW_FAR_DIST = 600
const LABEL_TEXT_HEIGHT_FAR = 5.0
const LABEL_TEXT_HEIGHT_NEAR = 6.0
const ZOOM_IN_LIMIT_RATIO = 0.6
const FOCUS_NODE_DISTANCE = 10

function getNodeCoreSize(node) {
  return 1.0 + Math.pow((node.val || 1) / MAX_VAL, 0.6) * 5.0
}

function getClampedValRatio(val) {
  const safeVal = Math.max(0, Number(val || 0))
  return Math.max(0, Math.min(1, safeVal / MAX_VAL))
}

// ── 主 Composable ──────────────────────────────────────────────────
export function useKnowledgeGraph(containerRef) {
  let graph = null
  let nodeMap = {}
  let autoRotateTimer = null
  let autoRotating = false
  let minZoomDistance = null
  let currentLabelTextHeight = LABEL_TEXT_HEIGHT_FAR
  const ROTATE_SPEED = Math.PI / 600

  // 用 shallowRef 存储需要在模板中响应的状态
  const graphData = shallowRef({ nodes: [], links: [] })
  const highlightNodes = shallowRef(new Set())
  const highlightLinks = shallowRef(new Set())
  const selectedNode = shallowRef(null)
  const categories = shallowRef([])
  const hiddenCategories = shallowRef(new Set())
  const isRotating = shallowRef(false)

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

  function getCameraDistance() {
    if (!graph) return 0
    const camera = graph.camera()
    const controls = graph.controls?.()
    if (controls?.target) return camera.position.distanceTo(controls.target)
    return camera.position.length()
  }

  function setupZoomLimits() {
    if (!graph) return
    const controls = graph.controls?.()
    if (!controls) return
    const baseDistance = getCameraDistance()
    if (!baseDistance) return
    minZoomDistance = baseDistance * ZOOM_IN_LIMIT_RATIO
    controls.minDistance = minZoomDistance
  }

  function getLabelTextHeightByDistance(dist) {
    const span = LABEL_SHOW_FAR_DIST - LABEL_SHOW_NEAR_DIST
    if (span <= 0) return LABEL_TEXT_HEIGHT_FAR
    const t = Math.max(0, Math.min(1, (dist - LABEL_SHOW_NEAR_DIST) / span))
    return LABEL_TEXT_HEIGHT_NEAR + t * (LABEL_TEXT_HEIGHT_FAR - LABEL_TEXT_HEIGHT_NEAR)
  }

// ── Bloom 后处理（距离自适应）────────────────────────────────────                                                  
  let bloomPass = null                                                                                                  
  const BLOOM_FAR_DIST = 500    // 远处全强度                                                                           
  const BLOOM_NEAR_DIST = 80    // 近处最低强度                                                                         
  const BLOOM_STRENGTH_MAX = 2.0                                                                                        
  const BLOOM_STRENGTH_MIN = 0.4                                                                                        

  function setupBloom() {
    try {
      bloomPass = new UnrealBloomPass()                                                                                 
      bloomPass.strength = BLOOM_STRENGTH_MAX 
      bloomPass.radius = 0.9
      bloomPass.threshold = 0.4
      graph.postProcessingComposer().addPass(bloomPass)
    } catch (e) {
      console.warn('Bloom post-processing unavailable, falling back to sprite glow only')
    }
  }
function updateBloomByDistance() {                                                                                    
    if (!bloomPass || !graph) return                                                                                    
    const dist = getCameraDistance()                                                                       
    // 线性插值：远处满强度，近处降到最低                                                                               
    const t = Math.max(0, Math.min(1, (dist - BLOOM_NEAR_DIST) / (BLOOM_FAR_DIST - BLOOM_NEAR_DIST)))                   
    bloomPass.strength = BLOOM_STRENGTH_MIN + t * (BLOOM_STRENGTH_MAX - BLOOM_STRENGTH_MIN)                             
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
    const valRatio = getClampedValRatio(val)
    const brightness = 0.4 + 0.6 * Math.pow(valRatio, 0.3)

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
      opacity: (0.15 + valRatio * 0.2) * brightness,
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
    if ((node.val || 0) < LABEL_MIN_ASSOCIATIONS) return null
    const label = new SpriteText(node.name)
    label.color = '#e0e0e0'
    label.textHeight = currentLabelTextHeight
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

  function toggleRotation() {
    isRotating.value = !isRotating.value
    if (!isRotating.value) {
      stopAutoRotate()
      clearTimeout(mouseIdleTimeout)
    } else {
      startAutoRotate()
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
    // 选中节点后固定展示其关联标签，避免仅旋转视角时被距离阈值误隐藏
    labelVisible = true

    applyHighlight()

    // 相机飞向节点
    const distance = Math.max(FOCUS_NODE_DISTANCE, minZoomDistance || 0)
    const originDist = Math.hypot(node.x || 0, node.y || 0, node.z || 0) || 1
    const distRatio = 1 + distance / originDist
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
    // 取消选中后恢复按当前缩放距离控制标签显隐
    checkZoomLevel()
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
      const valRatio = getClampedValRatio(val)
      const brightness = 0.4 + 0.6 * Math.pow(valRatio, 0.3)

      if (hasHighlight && !highlightNodes.value.has(node)) {
        if (core) core.material.opacity = 0.95 * brightness * 0.15
        if (innerGlow) innerGlow.material.opacity = 0.7 * brightness * 0.15
        if (outerHalo) outerHalo.material.opacity = (0.15 + valRatio * 0.2) * brightness * 0.15
        if (label) label.visible = false
      } else {
        if (core) core.material.opacity = 0.95 * brightness
        if (innerGlow) innerGlow.material.opacity = 0.7 * brightness
        if (outerHalo) outerHalo.material.opacity = (0.15 + valRatio * 0.2) * brightness
        if (label) label.visible = selectedNode.value ? true : labelVisible
      }
    })

    graph
      .linkOpacity(link => {
        if (!hasHighlight) return 0.22
        return highlightLinks.value.has(link) ? 0.7 : 0.03
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
        const srcId = typeof link.source === 'object' ? link.source.id : link.source
        const tgtId = typeof link.target === 'object' ? link.target.id : link.target
        const srcNode = nodeMap[srcId]
        const tgtNode = nodeMap[tgtId]
        if (!srcNode || !tgtNode) return false
        return !hiddenCategories.value.has(srcNode.category) && !hiddenCategories.value.has(tgtNode.category)
      })
  }

  // ── 缩放标签隐藏 ─────────────────────────────────────────────────
  let labelVisible = true
  function checkZoomLevel() {
    if (!graph) return
    const dist = getCameraDistance()
    const shouldShow = dist >= LABEL_SHOW_NEAR_DIST && dist <= LABEL_SHOW_FAR_DIST
    const lockLabelVisibility = Boolean(selectedNode.value)
    const nextLabelTextHeight = getLabelTextHeightByDistance(dist)
    const textHeightChanged = Math.abs(nextLabelTextHeight - currentLabelTextHeight) > 0.05

    if (textHeightChanged) {
      currentLabelTextHeight = nextLabelTextHeight
      graphData.value.nodes.forEach(node => {
        const label = node.__threeObj?.userData?.label
        if (label) label.textHeight = currentLabelTextHeight
      })
    }

    if (!lockLabelVisibility && shouldShow !== labelVisible) {
      labelVisible = shouldShow
      applyHighlight()
    }
    updateBloomByDistance()
  }

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

    // 构建 node lookup map（供 updateVisibility 使用）
    nodeMap = {}
    data.nodes.forEach(n => { nodeMap[n.id] = n })

    // 提取分类列表
    const cats = [...new Set(data.nodes.map(n => n.category).filter(Boolean))]
    categories.value = cats.map(c => ({ name: c, color: getCategoryColor(c) }))

    graph = new ForceGraph3D(containerRef.value, {
      controlType: 'orbit',
    })
      .backgroundColor('#000000')
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
        <div style="background:rgba(0,0,0,0.85);border:1px solid rgba(255,255,255,0.1);border-radius:8px;padding:10px 14px;color:#f0f0f0;font-size:12px;font-family:sans-serif;backdrop-filter:blur(12px);">
          <div style="font-weight:600;margin-bottom:4px;">${node.name}</div>
          <div style="color:rgba(255,255,255,0.5);font-size:11px;">分类：${node.category || '未知'}</div>
          <div style="color:rgba(255,255,255,0.5);font-size:11px;">关联：${node.val || 0} 个节点</div>
        </div>
      `)
      .nodeOpacity(1)
      // 边：曲线 + 可见颜色 + 无粒子
      .linkCurvature(0.15)
      .linkWidth(1.0)
      .linkOpacity(0.4)
      .linkColor(link => {
        const src = typeof link.source === 'object' ? link.source : null
        const color = src ? getCategoryColor(src.category) : '#ff6b4a'
        return new Color(color).lerp(new Color('#ffffff'), 0.15).getStyle()
      })
      .linkDirectionalParticles(0)
      // 交互
      .onNodeClick(handleNodeClick)
      .onNodeHover(handleNodeHover)
      .onBackgroundClick(clearHighlight)
      // 分类筛选
      .nodeVisibility(node => !hiddenCategories.value.has(node.category))
      // 力模拟
      .d3AlphaDecay(0.02)
      .d3VelocityDecay(0.3)
      .cooldownTime(8000)
      .graphData(data)

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

    // 力模拟稳定后，计算精确的聚类质心边捆绑
    graph.onEngineStop(() => {
      computeLinkBundling()
    })

    // Bloom
    setupBloom()
    setupZoomLimits()

    // 深度雾：远处物体自然淡出
    graph.scene().fog = new FogExp2(0x000000, 0.0008)

    // 星空粒子
    addStarField()

    // 事件监听
    window.addEventListener('resize', handleResize)

    // 缩放检查
    graph.controls().addEventListener('change', checkZoomLevel)
    checkZoomLevel()
  }

  // ── 生命周期 ──────────────────────────────────────────────────────
  function pause() {
    if (graph) graph.pauseAnimation()
    stopAutoRotate()
    window.removeEventListener('resize', handleResize)
  }

  function resume() {
    if (graph) graph.resumeAnimation()
    window.addEventListener('resize', handleResize)
    handleResize()
  }

  function destroy() {
    pause()
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
    minZoomDistance = null
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
