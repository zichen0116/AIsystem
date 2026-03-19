High emit 会未定义，按计划做会直接报错
在 selectConversation 里用了 emit(...)，但后面还是 defineEmits([...]) 没接收返回值。
参考：plan.md:357、plan.md:424
应改成：const emit = defineEmits([...])。

High startNewConversation 的示例会把现有清理逻辑“抹掉”
示例只清状态，没保留当前代码里的 abortController?.abort()、clearTimeout(saveTimer)、destroyEditor() 等清理，容易出现流式请求未中断/定时器残留。
参考：plan.md:539
建议写成“在现有函数上增量修改”，不要整段替换。

Medium 生命周期计划还不够干净
你已经要求去掉 onActivated 的 loadLatest，但计划里保留了一个空 onActivated，同时还保留 isFirstMount 语义，容易让实现者困惑。
参考：plan.md:470
建议：直接删 onActivated 相关自动恢复逻辑与 isFirstMount 变量，保持“每次进入默认新会话”。

Medium 侧边栏历史只在 onMounted 拉一次，后续可能不刷新
计划只写了 onMounted -> loadHistory()。新生成会话后，侧边栏可能不立即出现新记录。
参考：plan.md:390
建议加一个最小机制：生成完成后触发一次 loadHistory（比如父组件事件或 defineExpose 调用）。

Low 计划写了新增 schema，但路由示例没用 response_model
会导致 schema 形同虚设、接口契约容易漂移。
参考：plan.md:109、plan.md:183、plan.md:237

Low 文件清单写了要新增测试文件，但任务里主要是手工测试
参考：plan.md:21
建议二选一：要么补最小 API 自动化测试，要么把“新增测试文件”从范围里去掉。