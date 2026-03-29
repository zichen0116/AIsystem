严重：2FA 临时 token 的隔离假设与现有鉴权实现不一致，存在越权风险
设计文档要求 2fa_pending token 不能访问其他接口（design.md#L84）。
但当前鉴权链路里，decode_access_token 并不校验 type，且缺少 version 时默认 1（jwt.py#L50）；get_current_user 直接信任该结果（auth.py#L27）。
实现文档也未要求改 decode_access_token/get_current_user 去拒绝 type=2fa_pending（plan 只新增 create/decode_2fa_pending_token，见 plan.md#L566）。
2fa_pending token 被“硬拒绝”在 decode_access_token，还是在 get_current_user 里拒绝（两种都可，但需明确唯一策略）
高：实现文档中的 schema 定义不完整，后续步骤会引用未定义类型
实现文档 Task4 的 auth.py schema 示例到 Toggle2FA 就结束（plan.md#L350）。
但后续又要求在登录 2FA 流程中使用 TwoFARequired / Login2FAVerify（plan.md#L607, plan.md#L536）。
设计文档明确这两个 schema 应存在（design.md#L117）。
高：Task 7 的代码块存在污染/重复，按文档复制会产生无效代码
从 open2FAModal 后开始出现不完整重复片段（如孤立的 method: 'POST'），并整段重复手机号/邮箱/2FA 逻辑（plan.md#L1026, plan.md#L1042, plan.md#L1056）。
这会直接降低可执行性，且容易引入重复声明。
中：实现文档有轻微漂移/可维护性问题
send-email-code 已改成仅 current_user，但 imports 仍包含 SendEmailCodeRequest（plan.md#L410, plan.md#L480）。
这不是阻塞问题，但会误导执行者。
低：步骤编号有重复，执行追踪容易混乱
Task3 出现两个 Step 2（plan.md#L144, plan.md#L151）。
Task8 在 Step 10 后又回到 Step 9（plan.md#L1631, plan.md#L1638）。