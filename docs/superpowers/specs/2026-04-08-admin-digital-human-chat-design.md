# Admin Digital Human Intro and Chat Design

> Date: 2026-04-08
> Status: Implemented v1

## Overview

管理员端数字人第一版不接知识库，只承担两个能力：

1. 稳定介绍 EduPrep、管理员端与数据中台大屏。
2. 与管理员进行轻量闲聊，并把后端生成的回答交给讯飞数字人播报。

本次改造的核心目标是替换现有“语音识别结果原样 `writeText` 播报”的链路，避免数字人复读用户原话，并支持短上下文对话。

## Decisions

| 决策点 | 结论 |
| --- | --- |
| 项目介绍来源 | 后端固定模板，不接知识库 |
| 闲聊生成方式 | 复用现有 LLM service |
| 会话记忆 | 前端组件内保留最近 3 轮，随请求发送 |
| 数据持久化 | v1 不落库，不增加会话表 |
| 实时数据 | v1 不接入大屏实时指标查询 |
| 数字人职责 | 只展示形象与播报文本，不负责问答理解 |

## Backend Design

### API

- 新增 `POST /api/v1/digital-human/admin/chat`
- Request:
  - `message: string`
  - `history: { role, content }[]`
- Response:
  - `answer: string`
  - `speak_text: string`
  - `mode: "intro" | "chat"`

### Routing Strategy

- 命中“项目介绍 / 系统介绍 / 平台介绍 / 大屏介绍 / 数据中台介绍”类问题时，直接返回固定介绍模板。
- 其他问题进入 LLM 闲聊链路。

### Prompt Strategy

- system prompt 固定包含：
  - 角色：EduPrep 管理员端数字人
  - 能力：介绍项目与管理员端，支持轻量闲聊
  - 边界：不知道的实时数据、未接入能力、内部事实不能编造
  - 输出风格：简短、自然、适合口播

### Speak Text Sanitization

- 去掉 Markdown 符号、列表标记和多余换行
- 压缩为空格分隔的自然短句
- 长回复裁剪到适合播报的长度
- LLM 失败或空回复时返回固定兜底话术

## Frontend Design

### New Voice Flow

管理员端数字人语音链路改为：

`语音识别 -> 调后端管理员聊天接口 -> 数字人播报回答`

不再把识别结果直接 `writeText` 给数字人。

### Conversation Memory

- 组件内维护 `conversationHistory`
- 仅保留最近 6 条消息（3 轮）
- 每次请求将最近窗口随 `message` 一起发给后端
- 关闭数字人或离开页面时清空历史

### State Machine

- `idle`
- `listening`
- `waiting_reply`
- `speaking`

### Anti-duplication Rules

- 同一轮识别结果只提交一次
- `waiting_reply` / `speaking` 状态下忽略新的识别结果
- 短时间内相同 `message` 不重复提交
- 短时间内相同 `speak_text` 不重复播报
- 播报结束后再自动进入下一轮监听

## Error Handling

- 语音识别失败：记录错误并回到可恢复状态
- 后端请求失败：播报固定兜底回复
- LLM 无回复：后端返回默认闲聊兜底
- 数字人播报失败：恢复到空闲态并允许下一轮重新开始

## Acceptance Criteria

- 介绍类问题返回固定、稳定、非复读式答案
- 连续追问时能结合最近几轮上下文作答
- 单次语音输入只触发一次请求和一次播报
- 播报中不会再次识别并提交残留文本
- 相同识别文本和相同返回文本在短时间内不会重复播报
