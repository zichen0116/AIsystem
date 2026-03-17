High 文档内部有自相矛盾，开发会无所适从
在示例代码里，任一接口失败就直接 return（不恢复任何内容）
design.md:343
但降级策略又写“消息失败时只加载教案内容”
design.md:474
这两处必须统一成一种行为。
High “每次进页面默认新会话”还没覆盖到现有 onActivated 逻辑
文档只写了改 onMounted 去掉 loadLatest
design.md:321
但当前代码还有 onActivated -> loadLatest()，会再次自动恢复历史：
LessonPlanPage.vue:379
LessonPlanPage.vue:381
文档应明确“同时移除/禁用 onActivated 的自动恢复”。

Medium “无需迁移”与“要求 updated_at 索引”冲突
文档一处要求确保 updated_at 有索引
design.md:153
design.md:234
另一处又写无需改表/无需迁移
design.md:656
竞赛+YAGNI建议：删掉“必须加索引”的要求。

Medium 教案快照过滤规则是启发式，需标注“竞赛版折中”
当前规则：startsWith('#') && len>100
design.md:227
design.md:425
可用，但建议文档明确这是临时规则，避免被误认为精确语义分类。