

# 现在需要完善RAG系统的后端部分，要求如下：

现有的分块逻辑为主调用语义分块，递归分块负责兜底有问题，你认为这种方案对于此次教学智能体赛题的项目合理吗？要不要采取其他方案？
现有方案需要优化的点如下：

1. 语义分块，默认正则只认英文句号 `.`、问号 `?`、感叹号 `!` 后跟空格作为句子边界，**完全不支持中文标点**（`。`、`？`、`！`等）。对于中文教育场景，这意味着整段中文文本不会被拆分成句子，导致语义分块几乎失效。中文句子后通常没有空格（`\s+`）

2. 修复建议：

   在 [split_documents_semantic](vscode-file://vscode-app/d:/DevelopTools/VScode/resources/app/out/vs/code/electron-browser/workbench/workbench.html) 中传入自定义的 `sentence_split_regex`：

   ```
   text_splitter = SemanticChunker(
       embeddings=embeddings,
       sentence_split_regex=r"(?<=[.?!。？！；\n])\s*",  # 支持中文标点，允许无空格
       breakpoint_threshold_type=breakpoint_threshold_type,
       breakpoint_threshold_amount=breakpoint_threshold_amount,
       min_chunk_size=min_chunk_size,
       add_start_index=True
   )
   ```

   关键改动：

   - `[.?!。？！；\n]` — 加入中文句号、问号、感叹号、分号、换行
   - `\s*` 替换 `\s+` — 中文标点后通常无空格

3. 递归分块缺少 `？`、`！`、`；`，

4. 建议优化：

   separators = [
       "\n\n\n",   # 段落分隔（三个换行）
       "\n\n",     # 段落分隔（两个换行）
       "\n",       # 换行
       "。",       # 中文句号
       "？",       # 中文问号
       "！",       # 中文感叹号
       "；",       # 中文分号
       ". ",       # 英文句子
       "? ",       # 英文问号
       "! ",       # 英文感叹号
       "，",       # 中文逗号
       ", ",       # 英文逗号
       " ",        # 空格
       ""          # 单字符
   ]
