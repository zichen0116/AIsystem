为什么对话历史你选择不做服务端持久化？这么重要的数据怎么能不放到数据库呢？
1. pypandoc 的系统级依赖陷阱（部署必坑）
文档中的问题：实施文档中写了 pip install pypandoc，并在 export_docx 接口中直接调用了 pypandoc.convert_text()。
隐患在哪：pypandoc 只是一个 Python 壳子，它的底层严重依赖于操作系统里是否安装了 pandoc 软件（比如 Ubuntu 需要 apt-get install pandoc）。如果在评委演示或部署到新服务器时，系统没装 pandoc，这个 DOCX 导出接口会直接报错 500 崩溃。
修复建议：在 backend/app/api/lesson_plan.py 中，在调用前增加自动下载逻辑，或者在系统启动时检查下载。
code
Python
# 建议在 lesson_plan.py 顶部或 export_docx 中加入：
import pypandoc
try:
    pypandoc.get_pandoc_version()
except OSError:
    logger.info("Pandoc 未安装，正在自动下载...")
    pypandoc.download_pandoc()
2. Tiptap 的 Notion 风格菜单“光装不用”
文档中的问题：实施文档的 npm install 步骤中包含了 @tiptap/extension-floating-menu 和 @tiptap/extension-bubble-menu，在文档里也标为“可选（提升体验）”，但是！在 LessonPlanEditor.vue 的代码实现中，根本没有用到这两个扩展。
隐患在哪：如果没有这两个菜单，你的右侧编辑器就是一个普通的纯文本输入框，完全体现不出“豆包/Notion”的高级感，评委视觉体验大打折扣。
修复建议：让 Claude 在 LessonPlanEditor.vue 的 <template> 中加入 <bubble-menu> 和 <floating-menu> 组件。（这花不了几分钟，但视觉效果提升是量级的）。
高：SSE 错误会被吞掉，前端可能“报成功但实际失败”。
证据：processSSEStream 里 throw new Error(data.error) 又被同一层 catch 吃掉，且调用前未检查 res.ok。
参考：2026-03-13-lesson-plan-generation.md:1814, 2026-03-13-lesson-plan-generation.md:1828, 2026-03-13-lesson-plan-generation.md:1905, 2026-03-13-lesson-plan-generation.md:1913

高：上传格式与解析能力不一致，pptx 会走“二进制转文本”降级，质量会很差；同时未覆盖赛题强调的视频演示链路。
证据：前端允许 .pptx，解析器工厂不支持 .pptx，失败后直接 decode 原始字节；赛题要求支持 PDF/Word/PPT/图片/视频，并强调至少两种格式（示例含视频）。
参考：2026-03-13-lesson-plan-generation.md:1355, 2026-03-13-lesson-plan-generation.md:512, 2026-03-13-lesson-plan-generation.md:516, factory.py:50, factory.py:58, 赛题信息.md:87, 赛题信息.md:125

高：鉴权设计前后不一致。设计写“所有教案端点都要 JWT”，但计划代码里 export/docx 没有用户依赖，upload 还是可空用户参数。
参考：2026-03-13-lesson-plan-generation-design.md:232, 2026-03-13-lesson-plan-generation.md:499, 2026-03-13-lesson-plan-generation.md:527

高：Pandoc 可用性假设不闭环。设计里写“首次自动下载 Pandoc”，但实施代码没有 download_pandoc()，现场环境若没 Pandoc 会直接导出失败。
参考：2026-03-13-lesson-plan-generation-design.md:16, 2026-03-13-lesson-plan-generation-design.md:305, 2026-03-13-lesson-plan-generation.md:537

中：对话历史设计与实现不一致，AI 聊天区并没有沉淀真实 AI 内容，后续“基于历史理解意图”效果会弱。
证据：生成/修改后只追加固定文案“教案已生成/已更新”，不是模型回复内容。
参考：2026-03-13-lesson-plan-generation-design.md:41, 2026-03-13-lesson-plan-generation-design.md:179, 2026-03-13-lesson-plan-generation.md:1829, 2026-03-13-lesson-plan-generation.md:1869

中：TOC“当前标题高亮”在计划实现里缺失。设计要求 Intersection Observer，但主容器里 activeHeadingIndex 只初始化不更新。
参考：2026-03-13-lesson-plan-generation-design.md:166, 2026-03-13-lesson-plan-generation.md:1759, 2026-03-13-lesson-plan-generation.md:1800

中：切 tab 取消请求的要求没真正落地。设计要求“切换 tab abort”，实现只有 onBeforeUnmount，若页面是 keep-alive，切 tab 不会触发卸载。
参考：2026-03-13-lesson-plan-generation-design.md:185, 2026-03-13-lesson-plan-generation.md:1924

中：LessonPlanChat 里 onMounted 重复，知识库会请求两次。
参考：2026-03-13-lesson-plan-generation.md:1400, 2026-03-13-lesson-plan-generation.md:1494

中：文件存储方案过于“临时”，file_id 不绑定用户、不持久化，重启后失效且存在跨用户误用风险。
参考：2026-03-13-lesson-plan-generation.md:367, 2026-03-13-lesson-plan-generation.md:380, 2026-03-13-lesson-plan-generation.md:292

中：和赛题“主动澄清需求并总结确认”的评分点贴合不够。当前方案是“用户输入即生成/修改”，缺少明确的澄清轮次策略。
参考：赛题信息.md:85, 2026-03-13-lesson-plan-generation-design.md:40