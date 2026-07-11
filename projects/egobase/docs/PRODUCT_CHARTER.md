# EgoBase Product Charter

**Status:** working hypothesis for R0 validation

**Updated:** 2026-07-12

## Product Job

当 EgoLink 佩戴者离开家庭或出现值得关注的定位/安全事件时，家庭成员需要获得连续、
可信、不过度采集的上下文，并能依据预先约定的策略采取行动，而不是依赖一个不透明的
云端账号或一次性的 AI 回答。

## Product Promise

EgoBase 在用户控制的环境中持续运行，保存设备与家庭的长期状态，接收最小必要证据，
应用本地策略，选择合适模型，并把提醒与行动完整记录下来。

## Initial Users

- 佩戴 EgoLink 的家庭成员；
- 管理设备、联系人和策略的家庭管理员/照护者。

R0 必须进一步选定一个具体关系和场景，不能同时覆盖老人、儿童、户外运动和独居安全。

## R0 Scope

In scope:

- 单个家庭、单个 EgoBase、1-3 个 EgoLink 设备；
- 设备身份与配对；
- location/safety event 接入；
- 最小 Evidence manifest；
- 家庭策略与联系人；
- 提醒、确认、action result 和 audit；
- 本地 PC reference runtime；
- 离线缓存与恢复验证。

Out of scope:

- 专用 EgoBase 硬件；
- 通用 NAS、智能家居或聊天助手；
- 多租户企业系统；
- 公网 Agent/算力市场；
- 未经授权的原始音视频持续采集；
- 对外宣称医疗、救援或量产安全能力。

## Acceptance Gates

R0 只有同时满足以下证据才可进入硬件讨论：

1. EgoLink 与 EgoBase 使用版本化契约完成可回放闭环；
2. 事件重复、乱序和断网补传不会产生重复动作；
3. 每条提醒可追溯事件、证据、策略和处理结果；
4. 连续 7 天运行，有事件到达率、延迟、失败和恢复报告；
5. 用户能理解为什么收到提醒，并能撤销/修改策略；
6. 数据导出、删除、设备丢失和重新配对有明确路径；
7. 证明专用硬件能解决现有 PC 方案的具体问题，而不是只提供更多算力。
