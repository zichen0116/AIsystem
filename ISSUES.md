High: 路由参数方案在计划内前后不一致，Claude Code 很容易按错一版实现。2026-04-06-courseware-management.md#L997 里卡片点击传的是 tab + projectId/lessonPlanId，但 2026-04-06-courseware-management-design.md#L204 定的是 mode=ppt&projectId 和 mode=lesson-plan&id，而计划后面的路由处理又写成读 projectId 和 lessonPlanId，2026-04-06-courseware-management.md#L1243。这会直接导致实现分裂。建议在计划里只保留一套参数契约，和设计文档完全一致。

High: Task 1 的模型修改示例和仓库当前 ORM 风格不一致，按计划抄会写错。2026-04-06-courseware-management.md#L48 开始用的是 Column(...) 写法，但真实模型是 SQLAlchemy 2 typed style Mapped + mapped_column，courseware.py#L7。这不是小问题，Claude Code 如果照计划机械执行，第一步就可能把模型风格写乱。建议把计划里的代码片段改成仓库现有风格，避免误导。


Medium: 计划里有几处“看起来能写，其实和现有代码不完全对得上”的实现细节，建议先修正文案，不然 Claude Code 会踩坑。
2026-04-06-courseware-management.md#L435 这段想在 oss_upload(file, user_id) 之后再 seek/tell 取文件大小，但现有 oss_service.py#L60 已经把文件流读掉了，这个写法不稳。
2026-04-06-courseware-management.md#L1279 用 project.cover_image_url 判断 PPT 跳转 phase，但当前 pptStore.fetchProject() 拿到的 projectData 并没有这个字段，ppt.js#L98。这里应该直接复用 PptHistory 现成判断逻辑，别在计划里写一个不存在的字段。

