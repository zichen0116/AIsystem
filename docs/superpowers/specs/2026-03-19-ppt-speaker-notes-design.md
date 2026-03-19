# PPT Speaker Notes Design

**Date:** 2026-03-19  
**Status:** Draft approved in conversation, pending file review

## Goal

为 PPT 大纲中的每一页自动生成并持久化保存 `speaker_notes`，让预览区右下角的“演讲备注”随当前页切换显示，并支持用户在大纲卡片中编辑备注内容。

## Current Problem

当前预览区的“演讲备注”面板读取的是 `currentResult?.speaker_notes`，但后端的 PPT 结果结构里并没有真正生成或存储该字段。结果是：

- 大纲阶段没有每页备注
- 生成 PPT 后也没有每页备注可读
- 预览区始终显示“暂无演讲备注”
- 用户再次打开会话时也无法恢复备注内容

## Recommended Approach

采用“在大纲卡片阶段生成并保存每页备注”的方案，把 `speaker_notes` 作为 `outline_payload.sections[].pages[]` 的一部分，与标题、正文、图片候选一起成为结构化大纲的持久化数据。

这是最稳妥的方案，因为：

- 备注和页面天然一一对应
- 备注能随着大纲一起保存、编辑、回显
- 预览区只需要读取当前页对应的备注，不依赖文多多额外返回字段
- 不会把备注强行塞进 PPT 页面正文，避免影响排版

## Data Model Changes

### Outline Payload

在每个 page 节点下新增字段：

```json
{
  "id": "page-1",
  "title": "第 1 页：课程封面与导入",
  "subtitle": "",
  "blocks": [],
  "speaker_notes": "本页先用 20 秒说明课程主题与切入点，再通过“建筑为何能承载文化”引出后续内容。",
  "image_candidates": [],
  "selected_image_id": null
}
```

### Persistence

不新增独立表，继续复用现有的 `ppt_outlines.outline_payload` JSONB 存储。这样可以保证：

- 当前会话保存备注
- 历史版本保存备注
- 重新打开会话时仍可恢复备注

## Generation Flow

### Outline Generation

在后端把 markdown 转换为 `outline_payload` 后，为每一页补充 `speaker_notes`。生成原则：

- 紧扣本页标题和要点
- 语气适合教师课堂讲授
- 长度控制在 1 到 3 句
- 不与页面正文完全重复
- 优先提供“这一页怎么讲”的口语化说明

### Outline Editing

用户在大纲卡片中编辑时，允许修改：

- 一级标题
- 二级标题
- 页面标题
- 页面副标题
- 页面正文块
- 页面备注 `speaker_notes`

图片候选与图片选择逻辑保持现状，不开放图片内容编辑。

### PPT Generation

生成文多多 markdown 时，默认不把 `speaker_notes` 混入 PPT 主内容。备注只用于：

- 预览区右下角显示
- 会话恢复时回显
- 后续如需扩展导出讲稿，可复用

## Frontend Changes

### Outline Card

`OutlineCard.vue` 需要新增每页备注编辑区：

- 浏览态显示备注文本
- 编辑态允许直接修改备注
- 保存时跟随整个 `outline_payload` 一起提交

### Preview Panel

预览区不再读取全局 `currentResult?.speaker_notes`，而是基于当前激活页 `activeSlideIndex` 从当前大纲或当前结果关联的数据中读取该页备注。

目标行为：

- 切换缩略图时，备注同步切换
- 再次进入会话时，备注仍然存在
- 如果该页没有备注，则显示“暂无演讲备注”

## Data Resolution Priority

预览区的备注读取建议采用以下优先级：

1. 当前大纲 `currentOutline.outline_payload` 中当前页的 `speaker_notes`
2. 历史消息里的结构化 outline payload
3. 无值时显示占位文案

这样可以避免把备注绑定到 `ppt_result` 这种本来主要承载预览二进制数据的结构上。

## Error Handling

- 如果某页没有生成出备注，不阻断大纲生成或 PPT 生成
- 如果旧历史数据没有 `speaker_notes` 字段，前端按空值兼容
- 如果用户手动删除备注，预览区显示“暂无演讲备注”

## Testing Strategy

### Backend

- 测试 markdown 转 `outline_payload` 后能够补出每页 `speaker_notes`
- 测试保存/审批 outline payload 后备注不丢失
- 测试旧 payload 无 `speaker_notes` 时兼容读取

### Frontend

- 测试大纲卡片能展示和编辑 `speaker_notes`
- 测试切换当前页时备注同步变化
- 测试无备注时显示占位文案

## Non-Goals

本轮不做以下内容：

- 不把备注写入文多多页面正文
- 不把备注单独建表
- 不做讲稿导出能力
- 不做基于语音的备注朗读

## Summary

这次改动的核心是：把演讲备注前移到结构化大纲阶段，作为每页内容的一部分生成、编辑、保存和回显。这样备注会稳定、可持久化，也最符合当前页面原型和用户使用路径。
