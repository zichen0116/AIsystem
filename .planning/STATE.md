# State: 课堂预演文件上传链路

**Current Phase:** Phase 1 — 数据模型与文件上传接口
**Phase Status:** Not Started
**Overall Progress:** 0/4 phases complete

---

## Phase Status

| Phase | Name | Status |
|-------|------|--------|
| 1 | 数据模型与文件上传接口 | Not Started |
| 2 | 文件处理与页级解析管线 | Not Started |
| 3 | 讲稿生成与 TTS 语音合成 | Not Started |
| 4 | 前端播放适配与历史集成 | Not Started |

## Current Phase Details

**Phase 1: 数据模型与文件上传接口**

Requirements in this phase:
- [ ] MODEL-01: rehearsal_session + rehearsal_scene 模型扩展
- [ ] MODEL-02: 页级场景元数据字段
- [ ] MODEL-03: 可播放页数计算逻辑
- [ ] MODEL-04: 会话摘要信息
- [ ] UPLOAD-01: 预演模块文件上传入口
- [ ] UPLOAD-02: 50MB 上传限制
- [ ] UPLOAD-03: 30 页上限
- [ ] UPLOAD-04: 独立上传入口
- [ ] UPLOAD-05: 无文本补充输入
- [ ] STATE-01: 页面状态分类

Success Criteria:
- [ ] 数据库迁移成功，模型包含所需字段
- [ ] 前端可见独立文件上传入口
- [ ] 上传接口正确校验文件大小和页数
- [ ] 上传文件持久化到 OSS 并写入数据库

## Completed Phases

(none)

## Blockers

(none)

---

*State initialized: 2026-04-12*
*Last updated: 2026-04-12*
