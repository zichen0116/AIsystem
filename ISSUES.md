Review Findings（按严重级别）

高 上传接口的依赖注入写法会导致 FastAPI 路由声明错误。
计划里写的是 current_user: CurrentUser = Depends()，但 CurrentUser 本身已经是 Annotated[..., Depends(get_current_user)]，这里再写空 Depends() 是错误用法。
参考: 2026-03-27-knowledge-base-integration.md:375, auth.py:75

高 Task 10 的“只替换 script + 仅删文件上传块”会让 KnowledgeBase.vue 出现未定义方法，页面编译失败。
新 script 没有 deleteGlobalTag / createTagFromManager，但模板里这些点击事件仍存在；计划步骤也没要求删掉这些绑定。
参考: 2026-03-27-knowledge-base-integration.md:1205, 2026-03-27-knowledge-base-integration.md:1470, KnowledgeBase.vue:564, KnowledgeBase.vue:574

高 文件类型链路不闭环：计划允许 .mp3 上传，但后端解析器不支持音频，任务会稳定失败。
计划里把 mp3 映射到 audio 且前端 accept 了 mp3；但 ParserFactory 没有音频 parser，process_knowledge_asset 会进入失败状态。
参考: 2026-03-27-knowledge-base-integration.md:225, 2026-03-27-knowledge-base-integration.md:1660, factory.py:51, tasks.py:115

高 标签筛选 SQL 方案大概率在 PostgreSQL 上出错。
计划里用 @> 但字段定义是 JSON；该操作符通常用于 jsonb，当前写法风险很高。
参考: 2026-03-27-knowledge-base-integration.md:630, 2026-03-27-knowledge-base-integration.md:152, knowledge_library.py:26

中 验收文档地址写错：计划要求看 /docs，但项目实际是 /doc.html。
会导致按计划验收时误判“服务异常”。
参考: 2026-03-27-knowledge-base-integration.md:1746, main.py:32

中 多处命令是 Unix 风格，在当前 Windows PowerShell 环境不可直接执行。
比如 head / tail 出现在关键验证步骤。
参考: 2026-03-27-knowledge-base-integration.md:171, 2026-03-27-knowledge-base-integration.md:1490, 2026-03-27-knowledge-base-integration.md:1729

中 OSS 临时文件清理只放在成功路径，异常路径会残留 temp 文件。
计划把清理代码加在流程尾部，但不是 finally，解析失败/向量化失败时不会执行。
参考: 2026-03-27-knowledge-base-integration.md:979, 2026-03-27-knowledge-base-integration.md:983