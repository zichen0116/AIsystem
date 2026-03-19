High：/latest?session_id=xxx 这个设计语义不稳，容易拿错数据
当前 /latest 是“按 updated_at 取最近一条”，且没有 session_id 参数（lesson_plan.py:225, lesson_plan.py:231）。
建议：保留 /latest 兼容旧逻辑，同时新增 GET /lesson-plan/{lesson_plan_id}（详情）和 GET /lesson-plan/{lesson_plan_id}/messages（消息），不要复用 /latest 做“按会话查”。

High：侧边栏当前是 mock，且没有“选中历史会话”事件，前端流程还接不上
现在 LessonPlanSidebar 只渲染 mockHistory，点击只是本地改 activeId，没有向父组件发 select 事件（LessonPlanSidebar.vue:11, LessonPlanSidebar.vue:15, LessonPlanSidebar.vue:37, LessonPlanSidebar.vue:41）。
建议：新增 @select-conversation 事件，把 lesson_plan_id/session_id 抛给 LessonPlanPage。

Medium：你依赖 session_id 关联是可行的，但数据库层没有强约束
lesson_plans.session_id 唯一（lesson_plan.py:19），chat_history 只有 session_id+user_id，没有 FK 到 lesson_plans（chat_history.py:25, chat_history.py:30）。
建议：/{id}/messages 必须先校验该 lesson_plan_id 属于当前用户，再用其 session_id 查消息；最好后续补 lesson_plan_id FK，避免孤儿数据。

Medium：你的目标流程和现状有冲突
你说“打开页面显示欢迎界面，不加载历史”，但当前 onMounted 会自动 loadLatest()（LessonPlanPage.vue:336, LessonPlanPage.vue:374）。
建议：加开关（如 autoRestoreLatest）或改成仅在用户点“历史会话”时加载列表。

Medium：消息恢复策略建议后端化，别继续前端启发式过滤
当前前端用“#开头且长度>100”判断教案消息并过滤（LessonPlanPage.vue:356），这在历史恢复时会误伤正常回答。
建议：消息接口返回 type（chat/lesson_plan_snapshot）或后端直接返回 UI 需要的消息形态。