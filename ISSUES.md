高: 实现计划里的 Qwen TTS 请求体大概率写错了，按这版代码直接接很可能打不通。计划里现在写的是 input.messages + parameters.voice/speed：2026-04-09-classroom-rehearsal-mvp.md (line 366)，但 OpenMAIC 已验证可用的 qwen-tts 接法是 input.text + input.voice + language_type，速度映射到 parameters.rate：tts-providers.ts (line 292)。这不是小偏差，而是接口层面的高风险错误。
高: TTS 持久化链路没有真正落地，会直接伤到“可保存 / 可回放 / 可续播”。设计文档写的是“音频文件存 OSS”：2026-04-09-classroom-rehearsal-mvp-design.md (line 368)，但实现计划里的 tts_service 只是把 DashScope 返回的 audio_url 原样塞进动作里，根本没有下载并转存到 OSS：2026-04-09-classroom-rehearsal-mvp.md (line 354)。更关键的是，当前现成的 OSS 服务只支持 pdf/doc/docx/jpg/jpeg/png/mp4，没有音频 MIME，也只接 UploadFile，不能直接复用来传 TTS 生成的音频字节：oss_service.py (line 18)、oss_service.py (line 30)、oss_service.py (line 60)。也就是说，“复用现有 oss_service.py 存音频”这句目前并不成立。

中: 生成服务和前端 store 的事件契约不完整，partial / 场景级失败虽然在后端考虑了，但前端当轮生成过程看不到。后端会发 scene_error，并最终把会话标成 partial：2026-04-09-classroom-rehearsal-mvp.md (line 685)、2026-04-09-classroom-rehearsal-mvp.md (line 695)，但前端 store 的 _handleSSEEvent 根本没处理 scene_error，只认 session_created / outline_ready / scene_ready / complete / error：2026-04-09-classroom-rehearsal-mvp.md (line 1051)。这样用户在首次生成时只会看到“生成完成”，却不知道其实有些页失败了、当前会话只是 partial。


High: 课堂预演的生成架构建议正式收敛为“后端任务编排 + 页级增量持久化 + 前端实时预览”，不要再使用“一个 SSE 全包，前端靠事件流拼全部业务状态”的方案。这里要参考 OpenMAIC 的服务端任务式思路，而不是继续强化前端编排。需要明确以下约束：
- 前端/后端仍然是正常前后端项目，这里说的“客户端/服务端模式”指的是生成流程由谁主导编排。当前项目应采用“后端主导编排”，不是“前端逐步导演每一页生成”。
- 生成任务的业务真相必须以后端数据库为准，SSE 如果保留，只能作为进度通知通道，不能再承载全部状态与恢复逻辑；也可以直接改为 job + 轮询模式，风格上更接近 OpenMAIC 的服务端任务方案。
- 后端需要把预演会话和每一页的生成状态增量落库，前端预览页读取“当前已生成结果”，而不是依赖单条 SSE 把所有 scene 数据拼在内存里。
- 必须支持“边生成边查看”：某一页内容和动作生成完成后，该页即可进入可预览状态，不要求等待整个会话完成。
- 必须支持“哪一页失败马上知道”：建议引入明确的页级状态，例如 pending / generating / ready / failed，前端在生成页和历史页都能看到失败页信息。
- 必须支持“单页重试”：建议提供页级重试能力，例如按 session + scene_order 或 scene_id 重跑该页，而不是整场预演全部重来。
- 会话级状态仍然需要保留，但它应该是对页级状态的汇总，例如 generating / partial / ready / failed，而不是唯一状态来源。
- 如果最终采用 job 设计，推荐显式区分“生成任务”和“预演会话”：任务负责进度，会话负责可播放结果；如果不单独建任务表，也至少要把任务态字段补在会话上，并保持页级状态可查询。
- 生成预览页的目标应该是“实时查看当前已完成页 + 看见失败页 + 支持重试页”，而不是只显示一个总进度条。


High: TTS 方案也需要正式收敛为“临时 URL 仅作短时可用资源，正式回放必须依赖本项目自己的持久化音频资源”。这里要参考 OpenMAIC“先尝试 URL，再回退到本地/持久资源”的思路，但适配到当前系统的服务端会话模型。需要明确以下约束：
- Qwen TTS 返回的临时 audioUrl 不能作为长期回放资源使用。已确认该 URL 官方有效期约为 24 小时，因此不满足历史会话、续播、跨天回放的要求。
- 当前问题不是“OSS 不能存音频”，而是“现有 oss_service.py 的封装还不支持程序生成的音频字节上传”。不要误判为基础设施限制。
- 不要硬复用现有 upload_file(UploadFile, user_id) 这条用户上传接口来存 TTS 结果；建议新增底层能力，例如 upload_bytes / put_object_bytes，用于上传程序生成的音频内容。
- 页面内容和动作生成完成后即可落库并进入可预览状态；TTS 应作为后续异步补齐步骤，不能阻塞页面 ready。
- 如果 TTS 失败，该页仍然必须可播放，只是 speech 动作降级为计时播放；不要因为语音失败把整页强行判死。
- 播放优先级建议明确为：persistent_audio_url > temp_audio_url > 计时播放。也就是优先使用本项目自己的稳定音频地址；若稳定地址尚未就绪但临时 URL 仍可用，可短时先播临时 URL；两者都不可用时再降级计时。
- 可以先用轻量方案把音频状态内嵌到 speech action 或 scene 结构里，例如包含 temp_audio_url / persistent_audio_url / audio_status / duration；但如果实现中发现重试、清理、审计、状态追踪复杂度上升，允许立即升级为独立表，例如 rehearsal_audio_assets。
- 如果建立独立音频表，至少应包含：session 关联、scene 关联、action 标识、provider、voice、speed、source_text、status、temp_audio_url、persistent_audio_url、error_message、timestamps。
- 建议的状态语义可明确为：pending（未生成音频）/ temp_ready（已有临时 URL）/ ready（已持久化）/ failed（音频不可用，需计时降级）。不要只存一个 audioUrl 字段就结束。
- 设计文档和实现计划都应明确：本项目要吸收 OpenMAIC“优先 URL、再回退”的播放思路，但回退目标不应是浏览器本地 IndexedDB，而应优先是本项目自己的持久化音频资源体系，因为当前项目强调会话保存、跨设备访问和历史回放。
