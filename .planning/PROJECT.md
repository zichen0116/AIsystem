# 多模态AI互动式教学智能体 — 课堂预演文件上传链路

## What This Is

一个面向教师的全栈智能备课平台，当前已具备主题驱动的课堂预演、AI课件生成、知识库RAG等核心能力。本次项目聚焦于为课堂预演模块新增"文件上传驱动的预演"链路，让教师可以上传自己的 PDF/PPT/PPTX 文件，直接生成可播放、可保存、可回放的课堂预演会话。

## Core Value

教师上传自有课件文件后，系统自动完成页级解析、教学化讲稿生成和语音合成，形成完整可播放的课堂预演，与现有主题生成预演并存，最终让预演模块具备两条独立完整的主链路。

## Requirements

### Validated

- ✓ 主题驱动的课堂预演生成（SSE流式） — Phase 1-2 existing
- ✓ 预演播放页（幻灯片渲染 + 字幕 + 播放控制） — Phase 1-2 existing
- ✓ 预演历史列表与回放 — Phase 1-2 existing
- ✓ TTS 语音合成链路（DashScope） — Phase 1-2 existing
- ✓ OSS 文件存储服务 — existing
- ✓ PDF 解析能力（PyMuPDF） — existing
- ✓ PPT 转换能力（LibreOffice） — existing

### Active

- [ ] 预演模块内独立文件上传入口
- [ ] 支持 PDF / PPT / PPTX 上传（50MB限制，30页限制）
- [ ] PPT/PPTX 统一转 PDF 处理链路
- [ ] PDF 页级渲染为图片（PyMuPDF）
- [ ] 页级解析摘要提取
- [ ] 教学化讲稿生成（LLM，沿用 DashScope 配置）
- [ ] TTS 语音生成（沿用现有链路）
- [ ] 空白页/封底页自动跳过（保留记录与原因）
- [ ] 失败页兜底逻辑（降级可播放）
- [ ] 播放页图片模式适配（直接展示原页图片）
- [ ] SSE 流式生成（沿用现有预演体验）
- [ ] 会话资产持久化（原始文件、PDF、页图、讲稿、音频）
- [ ] 历史页区分来源（文件上传 vs 主题生成）

### Out of Scope

- 统一文件存储层改造 — 本阶段仅服务预演，不做通用平台
- 与 courseware / 课件中心打通 — 上传文件不侵入现有课件数据结构
- 从其他模块已上传文件创建预演 — 不跨模块关联
- 用户补充文本输入（主题/课程名/讲解要求表单） — 上传即用，无额外输入
- 聚焦/高亮/激光/白板/圆桌等扩展能力 — 动作收敛为 speech + 翻页
- 结构化重绘播放 — 以原页视觉为准
- 第四、五阶段规划 — 本阶段为预演能力收尾

## Context

- 技术栈：Python 3.11 / FastAPI + Vue 3 / Vite + Element Plus
- AI服务：DashScope（通义千问）为主要 LLM/Embedding/TTS
- 存储：PostgreSQL 15 + Redis 7 + ChromaDB + 阿里云 OSS
- 环境：LibreOffice 已安装（PPT→PDF转换），PyMuPDF 已有依赖
- 现有预演模型：RehearsalSession + RehearsalScene，支持 SSE 流式生成
- 现有播放引擎：SlideRenderer（elements树渲染），需对上传预演切换为图片模式
- 竞赛项目，代码在私有仓库，无密钥泄露风险

## Constraints

- **竞赛收尾**：本阶段为课堂预演能力的收尾版本，必须做到可交付
- **技术栈锁定**：Vue 3 + FastAPI，不引入新框架
- **模型一致**：围绕 rehearsal_session + rehearsal_scene 建模，不新建主表
- **文件限制**：50MB 上传上限，30 页上限
- **动作收敛**：仅 speech + 系统翻页，不扩展其他动作类型

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| 播放页采用图片模式 | 展示原页视觉，不走 elements 渲染，改动最小 | — Pending |
| PPT→PDF 用 LibreOffice | 环境已安装，renovation_service 已有参考实现 | — Pending |
| PDF→页图用 PyMuPDF (fitz) | 项目已有依赖，轻量无额外安装 | — Pending |
| SSE 流式生成 | 沿用现有预演体验，前端实时看到页级进度 | — Pending |
| 资产存储用 OSS | 沿用现有预演的 OSS 上传方式，稳定可靠 | — Pending |
| LLM 沿用 DashScope | 保持与现有预演一致的模型配置 | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-12 after initialization*
