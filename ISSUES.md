[High] 计划里的前端导入路径会直接构建失败（@/... 别名未配置）
实现文档使用了 http.js、useKnowledgeGraph.js、@/components/...（plan）。
但当前 Vite 配置没有 resolve.alias（vite.config.js），项目内也未使用 @ 别名。按文档实现会报 Failed to resolve import '@/...'。

[High] Mock API 的 limit 语义不完整：节点被截断，但边未截断，数据会不一致
文档代码里 nodes = poets[:limit]（plan），但 links 全量返回（plan）。
当 limit < 50 时会出现“边引用了不存在节点”的情况，3D 图会生成无名称/无分类的隐式节点，影响 tooltip、搜索和筛选逻辑。

[Medium] 鉴权参数写法不规范，存在实现歧义
文档示例把 current_user 写成 current_user: CurrentUser = None（plan）。
当前项目里同类接口都用 current_user: CurrentUser（knowledge.py）。建议统一写法，避免被误改成“可选用户”。

[Medium] 验证命令是 Unix 风格，和当前 PowerShell 环境不兼容
文档多处用了 cat | grep、head、/dev/null（plan plan plan）。
在你这个 Windows + PowerShell/CMD 环境下，这些步骤会直接卡住执行。
[Medium] “点击浮层外关闭”在当前结构下可能无法满足
FilterPopover/SearchPopover 的 backdrop 是 position: absolute; inset: 0，但它们是渲染在 GraphConsole 内（plan plan plan）。
这意味着“外部点击区域”通常只覆盖控制台局部，不是全屏区域，和预期交互有偏差。
两种常见方案：
Teleport to="body" + position: fixed; inset: 0（推荐）
把浮层放到页面根容器（不是控制台子元素）再做全屏遮罩

[Medium] 使用私有 API _destructor()，后续版本升级风险高
销毁逻辑调用 graph._destructor()（plan）。
这是私有方法，不是稳定契约；升级 3d-force-graph 后很容易出现不可预期行为。
优先用官方公开 API 做清理（暂停动画、移除事件监听、清空容器等）
如果暂时只能用 _destructor，至少要：
明确写“依赖某版本”
加兜底判断（比如方法不存在时走 fallback）
升级时做专项回归测试