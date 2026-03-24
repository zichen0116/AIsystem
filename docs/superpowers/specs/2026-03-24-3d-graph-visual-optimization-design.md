# 3D 知识图谱视觉优化 — 设计文档

## 概述

对现有 3D 力导向星空知识图谱（`useKnowledgeGraph.js`）进行视觉效果优化，从"默认 graph 可视化"提升到"宇宙星图"层级。综合 ChatGPT、Gemini、Codex 三方建议，实现多层发光节点、聚类质心边捆绑、宇宙色系、多层星空、力布局调优。

## 修改范围

仅修改一个文件：`teacher-platform/src/composables/useKnowledgeGraph.js`

不新增文件，不改变 API surface，不影响现有交互（点击、hover、搜索、筛选、旋转）。composable 的返回接口保持不变，`LessonPrepKnowledge.vue`、`GraphConsole.vue`、`FilterPopover.vue`、`SearchPopover.vue` 均无需修改。

## 技术栈

| 库 | 版本 | 用途 |
|---|---|---|
| 3d-force-graph | ^1.79.1 | 力导向图 API |
| Three.js | ^0.183.2 | WebGL 渲染 |
| three-spritetext | ^1.10.0 | 标签文字 |
| d3-force-3d | (transitive) | 力模拟 + forceCollide |

### 完整 import 列表（修改后）

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

注意：新增 `Group`、`Mesh`、`MeshBasicMaterial`、`SphereGeometry`、`FogExp2`、`Vector3`，以及 `forceCollide` 来自 `d3-force-3d`。

## 一、宇宙色系

### 现状
- 8 色 `COLOR_POOL` 数组 + `hashCategory()` 按字符 hash 分配
- 颜色分类感太强，像"关系图按社区着色"

### 方案
采用"宇宙色系调色板 + hash 分配 + 可选覆盖"三层结构，兼容未来任意分类：

```js
// 宇宙色调色板 — 蓝紫冷色域，替换原有的高饱和彩虹色
const COSMIC_PALETTE = [
  '#6ea8fe', '#b490f0', '#50c8b0', '#7888cc',
  '#c07090', '#60b880', '#8899aa', '#5c8abf',
]

// 可选：已知分类的手工覆盖（如需暖金强调核心人物）
const CATEGORY_OVERRIDE = {
  '文学领袖': '#f0c060',
}

function getCategoryColor(category) {
  if (!category) return COSMIC_PALETTE[0]
  if (CATEGORY_OVERRIDE[category]) return CATEGORY_OVERRIDE[category]
  // 对未知分类仍用 hash 分配，确保同一分类始终映射同一颜色
  let hash = 0
  for (let i = 0; i < category.length; i++)
    hash = category.charCodeAt(i) + ((hash << 5) - hash)
  return COSMIC_PALETTE[Math.abs(hash) % COSMIC_PALETTE.length]
}
```

新增辅助函数：
- `getNodeCoreSize(node)` — 幂律映射：`1.0 + Math.pow((val || 1) / MAX_VAL, 0.6) * 5.0`（val=1 → ~1.5, val=12 → 6）
- `MAX_VAL = 12` — 数据集最大关联数
- `LABEL_VAL_THRESHOLD = 5` — 可配置标签显示阈值

## 二、多层发光节点（对象复用方案）

### 现状
- 单层 `Sprite` + `SpriteMaterial`，所有节点"差不多亮"
- `applyHighlight()` 和 `checkZoomLevel()` 全量重建节点对象，存在内存泄漏和性能风险

### 方案

#### 节点结构
每个节点为 `THREE.Group`，包含三层：

| 层 | 类型 | 作用 |
|---|---|---|
| Core | `Mesh`(SphereGeometry + MeshBasicMaterial) | 小而亮的实心核心 |
| Inner Glow | `Sprite`(SpriteMaterial, AdditiveBlending) | 紧凑光晕，触发 bloom |
| Outer Halo | `Sprite`(SpriteMaterial, AdditiveBlending) | 大而淡的弥散光环 |

亮度因子 `brightness = 0.4 + 0.6 * pow(val/MAX_VAL, 0.3)`，让核心节点（苏轼）明显更亮，叶子节点暗淡。

#### 对象复用策略（Codex 关键修正）

**初始化时一次性创建**所有节点对象，将子对象引用存储在 `group.userData`：

```js
group.userData = { core, innerGlow, outerHalo, label }
```

通过 `node.__threeObj` 访问节点的 Three.js 对象（3d-force-graph 内部属性，由 ThreeDigest 自动设置）。不额外维护 nodeObjectMap，避免双源状态同步问题。访问时需 null guard。

**`applyHighlight()` 实现要点**：
- **移除**现有 `graph.nodeThreeObject(node => ...)` 调用（当前代码行 234），不再重建对象
- 遍历 `graphData.value.nodes`，通过 `node.__threeObj?.userData` 获取引用
- 修改 `core.material.opacity`、`innerGlow.material.opacity`、`outerHalo.material.opacity`
- 非高亮节点 opacity *= 0.05，高亮节点恢复原始 opacity
- 标签：非命中节点 `label.visible = false`

**`checkZoomLevel()` 实现要点**：
- **移除**现有 `graph.nodeThreeObject(node => ...)` 调用（当前代码行 317），不再重建对象
- 遍历 `graphData.value.nodes`，通过 `node.__threeObj?.userData.label` 获取引用
- 设置 `label.visible = shouldShow`
- `nodeThreeObjectExtend` 保持默认 false（Group 完全替代默认对象）

#### 标签策略（Codex 修正）
- 标签阈值保持 `val >= 5`（不降到 3）
- 提取为 `LABEL_VAL_THRESHOLD` 常量
- Zoom-out 超过 600 单位时隐藏所有标签（修改 `visible`，不重建）
- 高亮模式下非命中节点标签隐藏

## 三、聚类质心边捆绑

### 现状
- 直线边，`linkWidth: 0`，`linkOpacity: 0.12`
- 像"调试辅助线"，无流动感

### 方案：两阶段渲染

#### 阶段一：力模拟期间
使用基础曲线 + 流动粒子（力模拟尚未稳定，centroid 不准确）：

```js
.linkCurvature(0.15)
.linkWidth(0.3)
.linkOpacity(0.08)
.linkDirectionalParticles(2)
.linkDirectionalParticleSpeed(0.004)
.linkDirectionalParticleWidth(1.2)
```

边颜色混入深蓝 `#1a1a3e`（60% 混合），降低分类色刺眼感。

#### 阶段二：力模拟稳定后（onEngineStop）
计算聚类质心，为每条边算出精确的 curvature 和 curveRotation：

1. **计算质心**：按 `category` 分组，求每组节点位置平均值
2. **计算 per-link curvature**：
   - 对 link A→B，取中点 M
   - 取相关质心 C（同簇取簇心，跨簇取两簇心中点）
   - 将 M→C 向量投影到 AB 的垂直平面
   - `curvature = |投影| / |AB|`（clamp 到 [0.05, 0.6]）
3. **计算 per-link curveRotation**：
   - 3d-force-graph 的 `linkCurveRotation` 定义：在 0 旋转时，曲线弯向 link 与 XY 平面交线的方向。旋转角（弧度）绕 start→end 轴顺时针旋转曲线
   - 因此 curveRotation 必须相对于 XY 平面交线方向计算：
     - 取 link 方向向量 `D = B - A`（归一化）
     - 取 XY 参考向量 `refDir = normalize(D × (0,0,1) × D)`（link 与 Z 轴的双叉积投影到垂直平面）
     - 取 bundling 方向 `bundleDir = normalize(projPerp(M→C, D))`
     - `curveRotation = atan2(bundleDir · (D × refDir), bundleDir · refDir)`
3. **更新图谱**：调用 `.linkCurvature(link => ...)` 和 `.linkCurveRotation(link => ...)` 使用预计算值

**优势**：使用 3d-force-graph 原生曲线 API，保留内置粒子、透明度、颜色功能，无需自定义 `linkThreeObject`。

## 四、多层星空 + 深度雾 + Bloom

### 多层星空
替换单层 2000 粒子为三层：

| 层 | 数量 | 分布范围 | 粒子大小 | 透明度 |
|---|---|---|---|---|
| 远景 | 3000 | 6000 | 0.8 | 0.3 |
| 中景 | 800 | 3000 | 2.0 | 0.5 |
| 近景 | 150 | 1500 | 4.0 | 0.8 |

颜色统一为冷蓝白 `0xccddff`，启用 `sizeAttenuation`。

**降级**：若 FPS 低于目标，减少到两层或回退到单层 2000 粒子。

### 深度雾
`FogExp2(0x050510, 0.0015)` — 远处物体自然淡出到背景色。

### Bloom 调参（带降级）

```js
strength: 1.5    // was 2 — 稍降
radius: 0.75     // was 0.5 — 更宽弥散
threshold: 0.65  // was 0.8 — 更多层发光（不低于 0.65，避免 #aabbcc 标签触发 bloom）
```

标签颜色使用 `#aabbcc`（亮度 ≈ 0.58，低于 threshold 0.65，确保文字不被 bloom 糊掉）。

**降级策略**（Codex 建议）：`setupBloom()` 包裹 try-catch，若 `postProcessingComposer()` 不可用则静默降级，仅依赖 Sprite 自身 AdditiveBlending 发光。

## 五、保守力布局调优

### 参数

| 参数 | 同类 | 跨类 | 比率 |
|---|---|---|---|
| link distance | 35 | 50 | 1:1.4 |
| link strength | 0.6 | 0.3 | 2:1 |

- `charge`: `-60 - val * 10`，`distanceMax: 300`
- `collide`: `radius = coreSize * 1.5 + 3`，`strength: 0.7`
- `center`: `strength: 0.05`
- `d3AlphaDecay`: 0.02，`d3VelocityDecay`: 0.3
- `cooldownTime`: 8000（对 50 节点规模足够收敛；若节点数增长需重新评估）

**原则**：若数据主关系被破坏，优先保真而不是强追求聚簇美观。

**注意**：`onEngineStop` 在 `cooldownTime` 到期后触发，阶段二边捆绑依赖此时机。8000ms 对当前 50 节点 mock 数据集足够，但节点规模显著增长时可能不够收敛。

## 六、Bug 修复

### 链路可见性（Codex #8）
`updateVisibility()` 中 `link.source/target` 可能不是对象。构建 `nodeMap`（id → node）在 `initGraph` 时初始化，`updateVisibility` 通过 map 查分类，不再回退空字符串。

### 销毁模式（Codex #9）
`destroy()` 不再依赖私有 `_destructor`。改为：
1. 遍历所有节点 Group，对 core/innerGlow/outerHalo 调用 `.geometry.dispose()` / `.material.dispose()` 释放 GPU 内存
2. 遍历星空层，dispose geometry 和 material
3. `graph.pauseAnimation()`
4. `graph.controls().dispose()`（若存在）
5. `graph.renderer().dispose()`（若存在）
6. 清空 DOM
7. 兜底 `_destructor()`（若上述不够，注意此为 3d-force-graph 私有 API，受版本约束 ^1.79.1）

### linkWidth 一致性（Codex #7）
设为 0.3，与"可见纤细线"验收标准一致。

## 技术风险与降级策略

| 风险 | 降级 |
|---|---|
| `postProcessingComposer()` 不可用 | try-catch 静默跳过，仅用 Sprite glow |
| 标签过多导致性能下降 | 保持 `val >= 5` 阈值，zoom-out 隐藏 |
| 高亮/缩放频繁触发 | 对象复用，仅改 material 属性 |
| force 调参破坏结构 | 优先回退 link strength/distance |
| 聚类质心计算不准 | clamp curvature 到 [0.05, 0.6]，阶段一基础曲线兜底 |
| 星空粒子过多 | 若 FPS 不达标，减少到两层或回退单层 2000 粒子 |
| `__threeObj` 在未来版本变更 | null guard 保护，失败时静默跳过 highlight 更新 |

## 验收清单

### 视觉
1. 多层发光节点 — 核心球 + 内层光晕 + 外层弥散，苏轼最大最亮
2. 节点层次 — 叶子暗小，核心亮大
3. 曲线边 — 弧形，同簇边向质心汇聚形成光束
4. 流动粒子 — 小光点沿曲线流动
5. 宇宙色系 — 蓝紫为主，金色点缀
6. 多层星空 — 远密小，近稀大
7. 深度雾 — 远处自然淡出
8. Bloom — 弥散发光，文字不糊
9. 力布局 — 同派温和聚簇，不破坏数据关系

### 交互
10. 点击高亮 — 关联亮，其余暗（对象复用，不闪烁）
11. 点击恢复 — 空白区域恢复
12. Hover tooltip — 名字/分类/关联数
13. 标签筛选 — 弹出浮层
14. 搜索 — 匹配并飞向
15. 自动旋转 — 3秒无操作后

### 性能（Codex 新增）
16. FPS ≥ 30
17. 内存不持续增长（连续操作 1 分钟后稳定）
18. 连续点击/缩放 1 分钟后不掉帧
