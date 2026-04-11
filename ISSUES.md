High: RehearsalNew 的进度百分比算法会在 sessionId 模式下失真，可能一上来就接近或等于 100%。实现计划按 sceneStatuses.length / totalScenes 计算进度 phase2-plan (line 668) phase2-plan (line 671)，但后端会在大纲完成后预创建全部场景记录，初始就是 pending 状态 rehearsal_generation_service.py (line 308) rehearsal_generation_service.py (line 315)。这样轮询已有会话时，sceneStatuses.length 不是“已完成页数”，而是“总页数”。

Medium-High: partial / failed 会话在 RehearsalNew 中会被当成“成功完成”态展示。实现计划把所有非 generating 会话都设成 store.generatingStatus = 'complete' phase2-plan (line 728) phase2-plan (line 769)，而 progressStatus 又把 complete 映射成 success phase2-plan (line 674) phase2-plan (line 676)。这会把“部分完成/生成失败”的会话误呈现为完成态。

Medium: 设计文档要求播放页错误状态有“重试”按钮，但实现计划落成了“返回”按钮，和设计不一致。phase2-design (line 106) 要求错误提示 + 重试按钮；实现计划在错误态只给了 返回 phase2-plan (line 1171) phase2-plan (line 1174)。

Medium: 单页重试后的会话汇总状态不会自动刷新，Lab 页和 New 页可能继续显示旧状态。计划里的 handleRetry() 只调用 store.retryFailedScene() phase2-plan (line 797)，而当前 store 的 retryFailedScene() 只更新单页状态，不会重算 currentSession.status 或重新拉取整会话 rehearsal.js (line 197) rehearsal.js (line 205)。如果最后一个失败页被修复，页面仍可能停留在 partial/failed 视觉状态，直到手动刷新。