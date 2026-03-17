少考虑/需要补充的点：

问题 3 不仅是问题 1 的连带。
enterWriterMode 用的是 createEditor(currentMarkdown)，而 Markdown 正确装载路径是 loadContent。见 LessonPlanPage.vue、WriterEditor.vue。
还有一个关键后端风险他没提：
后端只有内容以 # 开头才写入 lesson_plan.content，否则只进 ChatHistory。见 lesson_plan_service.py。这会直接造成“对话里有正文，但文档内容为空”。
“按 # 开头过滤历史消息”方案可用但不稳，容易误伤普通 markdown 回复。更稳是后端给消息打类型（如 message_type=lesson_plan）再过滤。
小问题：writer 链路里文档卡片点击事件未完整上抛，交互不一致（不是主因，但建议一并修）。
建议修复策略（更稳）：

先修时序：isSending=false 后再做完成态装载，且“先装载编辑器，再清空流缓存”。
统一文档装载入口：所有“打开文档”都走 loadContent(markdown)。
后端取消 startswith('#') 作为持久化门槛，或至少加 content_kind/message_type。
/latest 按消息类型过滤，不用字符串启发式。