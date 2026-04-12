# Requirements: 课堂预演文件上传链路

**Defined:** 2026-04-12
**Core Value:** 教师上传 PDF/PPT/PPTX 文件，自动生成可播放的课堂预演会话

## v1 Requirements

Requirements for this milestone. Each maps to roadmap phases.

### 文件上传

- [ ] **UPLOAD-01**: 用户可在预演模块内上传 PDF/PPT/PPTX 文件发起预演
- [ ] **UPLOAD-02**: 上传文件大小上限 50MB，超限拒绝并给出明确提示
- [ ] **UPLOAD-03**: 上传文件页数上限 30 页，超限直接拒绝并给出明确提示，不做静默截断
- [ ] **UPLOAD-04**: 上传入口独立于预演模块，不与其他备课上传入口混用
- [ ] **UPLOAD-05**: 用户上传文件后不再补充任何文本输入，点击确认即进入生成流程

### 文件处理

- [ ] **PROC-01**: PDF 文件直接进入页级处理链路
- [ ] **PROC-02**: PPT/PPTX 文件先通过 LibreOffice 转为 PDF，再统一走页级处理
- [ ] **PROC-03**: 若 PPT/PPTX→PDF 转换失败，整会话直接失败，错误提示明确指出"转换失败"
- [ ] **PROC-04**: PDF 每页通过 PyMuPDF 渲染为图片（页图链），上传 OSS 用于播放展示
- [ ] **PROC-05**: PDF 每页提取文本内容（解析链），用于给 AI 生成讲稿

### 讲稿与语音

- [ ] **SCRIPT-01**: 为每个可播放页生成教学化讲稿，以单页解析结果为主，结合整份文件上下文适度教学化扩写
- [ ] **SCRIPT-02**: 讲稿风格类似老师现场讲解，不可脱离原页内容太远，不编造原页不存在的核心知识点
- [ ] **SCRIPT-03**: 为每个讲稿生成 TTS 语音，沿用现有 DashScope TTS 配置和链路
- [ ] **SCRIPT-04**: TTS 失败时页面仍可通过文本讲稿播放（计时播放降级）
- [ ] **SCRIPT-05**: 讲稿主生成失败时退化生成简化讲稿，不直接废弃整页

### 状态与兜底

- [ ] **STATE-01**: 页面状态至少区分：可播放页、自动跳过页、失败兜底页、真正不可恢复页
- [ ] **STATE-02**: 自动跳过明显空白页和封底页，保留跳过记录和跳过原因
- [ ] **STATE-03**: 自动跳过页不进入正常播放序列，但在会话里可见并显示跳过原因
- [ ] **STATE-04**: 页图已成功但解析/讲稿/TTS 失败时，优先保住该页可播放性
- [ ] **STATE-05**: 不要求所有页面全部成功后才可播放，部分页失败整会话仍可播放

### 数据模型

- [ ] **MODEL-01**: 围绕 rehearsal_session + rehearsal_scene 建模，增加会话级上传来源信息
- [ ] **MODEL-02**: 每个页级场景保留：原始页码、是否跳过、跳过原因、页图地址、页级解析摘要、讲稿文本、音频状态/地址、失败原因/兜底状态
- [ ] **MODEL-03**: 播放页的总可播放页数基于可播放场景数，不基于原始总页数
- [ ] **MODEL-04**: 会话详情/历史信息中可看到原始总页数、跳过页数、失败兜底页数等摘要

### 播放与交互

- [ ] **PLAY-01**: 用户点击确认后进入现有预演加载页（RehearsalNew），沿用已有体验和视觉结构
- [ ] **PLAY-02**: 加载页文案和进度说明体现"文件解析/页级讲稿/语音生成"
- [ ] **PLAY-03**: 生成完成后进入现有播放页，播放页核心保持现有播放器结构
- [ ] **PLAY-04**: 播放页对上传预演切换为图片模式，直接展示原页图片而非 elements 渲染
- [ ] **PLAY-05**: 翻页由系统自动控制，动作收敛为 speech + 系统翻页
- [ ] **PLAY-06**: 后端用 SSE 长连接流式推送页级进度，前端等待式体验

### 历史与持久化

- [ ] **HIST-01**: 上传生成的预演会话与普通预演在历史页并存，能体现来源是"文件上传预演"
- [ ] **HIST-02**: 历史页可再次打开该会话并继续播放此前生成的内容
- [ ] **HIST-03**: 原始文件、转换 PDF、页图、讲稿、音频及页级状态作为会话资产保存
- [ ] **HIST-04**: 会话资产不因页面刷新或会话关闭而丢失

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### 扩展能力

- **EXT-01**: 从其他模块已上传文件直接创建预演
- **EXT-02**: 用户补充文本输入（主题、课程名、讲解要求等表单）
- **EXT-03**: 聚焦、高亮、激光、白板、圆桌等扩展动作
- **EXT-04**: 结构化重绘播放（将上传页转为系统自有 slide 元素）
- **EXT-05**: 与 courseware / 课件中心打通

## Out of Scope

| Feature | Reason |
|---------|--------|
| 统一文件存储层改造 | 本阶段仅服务预演，不做通用平台 |
| 与 courseware 数据结构打通 | 上传文件不侵入现有课件数据 |
| 跨模块文件关联 | 不从其他模块已上传文件创建预演 |
| 聚焦/高亮/激光/白板/圆桌 | 动作收敛为 speech + 翻页 |
| 结构化重绘 | 以原页视觉为准 |
| 第四、五阶段规划 | 本阶段为预演收尾 |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| UPLOAD-01 | TBD | Pending |
| UPLOAD-02 | TBD | Pending |
| UPLOAD-03 | TBD | Pending |
| UPLOAD-04 | TBD | Pending |
| UPLOAD-05 | TBD | Pending |
| PROC-01 | TBD | Pending |
| PROC-02 | TBD | Pending |
| PROC-03 | TBD | Pending |
| PROC-04 | TBD | Pending |
| PROC-05 | TBD | Pending |
| SCRIPT-01 | TBD | Pending |
| SCRIPT-02 | TBD | Pending |
| SCRIPT-03 | TBD | Pending |
| SCRIPT-04 | TBD | Pending |
| SCRIPT-05 | TBD | Pending |
| STATE-01 | TBD | Pending |
| STATE-02 | TBD | Pending |
| STATE-03 | TBD | Pending |
| STATE-04 | TBD | Pending |
| STATE-05 | TBD | Pending |
| MODEL-01 | TBD | Pending |
| MODEL-02 | TBD | Pending |
| MODEL-03 | TBD | Pending |
| MODEL-04 | TBD | Pending |
| PLAY-01 | TBD | Pending |
| PLAY-02 | TBD | Pending |
| PLAY-03 | TBD | Pending |
| PLAY-04 | TBD | Pending |
| PLAY-05 | TBD | Pending |
| PLAY-06 | TBD | Pending |
| HIST-01 | TBD | Pending |
| HIST-02 | TBD | Pending |
| HIST-03 | TBD | Pending |
| HIST-04 | TBD | Pending |

**Coverage:**
- v1 requirements: 34 total
- Mapped to phases: 0
- Unmapped: 34 ⚠️

---
*Requirements defined: 2026-04-12*
*Last updated: 2026-04-12 after initial definition*
