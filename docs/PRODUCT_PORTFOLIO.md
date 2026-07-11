# Ego Product Portfolio

**Status:** working source of truth

**Updated:** 2026-07-12

## North Star

Ego 的目标不是制造一个无所不能的 AI 设备，而是建立一套由用户拥有、跨设备连续、
可解释且可授权的个人智能系统。

系统必须同时满足：

- 用户拥有长期数据与身份；
- 感知端只采集完成任务所需的最小证据；
- 复杂推理可以在本地、局域网或授权云端运行；
- 模型输出不能覆盖原始证据；
- 高风险行动必须获得授权；
- 每次访问、推理、决策和动作都可以审计。

## Product Map

| 产品/能力 | 用户角色 | 核心职责 | 当前形态 | 当前阶段 |
|---|---|---|---|---|
| Ego | 总产品系统 | 统一身份、产品边界、跨设备体验与路线 | 总项目与组合管理 | Portfolio reset |
| EgoLink | 随身节点 | 定位、低功耗感知、安全交互、4G 入口 | 双开发板工程验证，未来单板/定制 PCB | v0.1.0 Engineering Alpha，D2/D5 主线 |
| EgoBase | 家庭/本地可信中枢 | 长期状态、策略、设备协同、模型与算力选择、审计 | 先运行在 PC/迷你主机，专用硬件待验证 | Product reset |
| Ego Data Core | 软件底座 | Evidence、Enhancement、Work Graph、Brief、Policy、Audit | Python/FastAPI/SQLite 本地运行时 | v0.1 technical loop complete |
| Ego Operator | 受控行动能力 | 计划、授权、执行、验证、回滚 | Data Core dry-run + 旧 desktop-agent 资产 | Prototype / legacy review |
| Ego Cloud | 可选服务层 | 远程中继、设备更新、授权云增强 | 尚未正式定义 | Deferred |

## System Boundary

```text
EgoLink / PC / future devices
  -> versioned events and bounded evidence
  -> EgoBase trust boundary
       identity + policy + evidence + long-term state
       model/compute routing + action authorization + audit
  -> user surfaces and authorized actions
```

EgoLink 不保存完整家庭长期上下文；EgoBase 不接管随身端的低延迟安全反射；云端不成为
身份、策略和原始数据的唯一事实源。

## Shared Contracts

跨项目协作只允许通过版本化契约：

1. `device_hello`：设备身份、版本、能力和信任状态；
2. `observation_event`：定位、运动、电量、网络和用户交互的结构化观察；
3. `evidence_manifest`：原始证据引用、哈希、隐私等级、保留策略；
4. `safety_event`：候选、确认、升级和处置状态；
5. `base_command`：EgoBase 下发的有边界命令、授权范围和有效期；
6. `action_result`：执行结果、失败原因和验证证据；
7. `policy_snapshot`：适用于设备和事件的最小策略版本。

EgoLink 已有部分 schema，可作为 CONTRACT-001 的输入；EgoBase 不直接读取 EgoLink
内部数据库或 Dashboard 状态。

## Product Rules

1. 先定义用户任务，再定义硬件。
2. 先用现有 PC/AI PC/迷你主机证明闭环，再决定专用 EgoBase。
3. 算力、模型和协议是可替换供应，不是品牌定位。
4. 每个子项目只有一个当前 Demo 主线。
5. 工程完成度与产品验证度分开汇报。
6. 未经真实运行验证的指标必须标记为目标或假设，不得表述为能力。

## Current Portfolio Bet

近期最有价值的组合不是单卖 EgoBase，而是：

> EgoLink 提供真实、持续、低功耗的随身事件；EgoBase 提供家庭可信上下文、长期状态、
> 隐私策略和行动协同。

这条组合路线能利用 EgoLink 已有工程进展，也能给 Data Core 找到真实数据入口和明确的
用户任务。
