High: 设计文档要求把文件解析结果持久化到 PPTReferenceFile.parsed_content，但没有同步要求更新 PPTReferenceFileResponse 或相关查询接口返回这个字段，Claude Code 很容易只做“落库”不做“可查”。这会直接违背你“参考文件解析结果要持久化，且解析状态可查询”的目标。2026-04-07-ppt-file-generation-design.md 2026-04-07-ppt-file-generation-design.md 2026-04-07-ppt-file-generation-design.md
当前响应模型只暴露 parsed_outline，没有 parsed_content。banana_schemas.py

Medium: 设计文档把 outline_text 定义成“最终组合文本源”，但当前系统里这个字段已经被不同接口当成“原始输入文本”“AI 生成出的 outline 文本”“结构化 outline JSON 字符串”混合使用。现在不把这个语义说清楚，Claude Code 很容易继续把“生成输入源”和“生成结果”写进同一个字段，后续 outline 接口行为会变得更混乱。2026-04-07-ppt-file-generation-design.md 2026-04-07-ppt-file-generation-design.md 2026-04-07-ppt-file-generation-design.md
现有代码里同一个 outline_text 会被先读作输入，再被写成结构化结果或 AI 输出文本。banana_routes.py banana_routes.py banana_routes.py

Medium: 接口返回示例把 reference_file_id 写成固定返回字段，但这个接口允许“只有文本、没有文件”的情况；如果这里不明确写“无文件时返回 null 或省略”，Claude Code 很可能会为了对齐响应格式硬造一个空参考文件记录，或者把纯文本请求实现得很别扭。2026-04-07-ppt-file-generation-design.md 2026-04-07-ppt-file-generation-design.md