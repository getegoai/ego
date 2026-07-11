# Ego Repositioning Review - 2026-07

## Executive Conclusion

当前 Ego 的主要风险不是代码不足，而是产品层次长期混在一起：硬件终端、家庭算力、
个人数据系统、电脑 Operator、模型路由和长期记忆都曾被当成“Ego 的核心”。结果是每条
技术路线都有合理性，却缺少一个首发用户愿意持续使用的明确任务。

本次建议：

1. `Ego` 升级为总产品系统与品牌，不再等同于某台设备；
2. `EgoLink` 保持独立的随身安全定位产品线；
3. `EgoBase` 从“家庭算力路由基站”重新定位为“私有 AI 信任中枢”；
4. `Ego Data Core` 保留为 EgoBase 的软件底座，不再承担整个产品叙事；
5. 第一条验证链固定为 EgoLink -> EgoBase 的真实事件、长期状态、家庭策略和行动闭环；
6. 专用 EgoBase 硬件、通用 Compute Fabric 和模型优化在产品闭环前暂停。

## What Was Built

### Ego Data Core

2026-05-28 的定义是“本地优先、Evidence-first 的个人数据操作系统”。工程计划共 31 个
issue，目前完成 29 个，缺少：

- `EDC-012`：可选 OllamaAdapter；
- `EDC-024`：Compute Fabric 节点注册。

已经跑通文件/截图 Evidence、文档解析、检索、增强、Work Graph、Daily Brief、策略、
审计、action dry-run、API、CLI 和 Web UI。2026-07-12 重组前后全量测试均为
`135 passed`。

这证明了软件架构可行，但没有证明 EgoBase 产品成立。尚未验证真实持续数据源、
EgoLink 接入、家庭用户任务、长期留存、远程恢复、设备身份或专用硬件价值。

### EgoLink

EgoLink 是当前最清晰、最活跃的产品线。独立仓库最新状态核验到 2026-07-11，已有
`v0.1.0 Engineering Alpha`，当前工程链为：

```text
4G device -> LTE -> Message Hub -> Web Dashboard
          -> bounded field evidence -> D2/D5 location data flywheel
```

D1 链路已达到转入标准，D2 定位精度基线和 D5 数据飞轮正在推进。它仍不具备量产定位
精度、48 小时续航、正式呼叫/SMS 或主动安全模型的产品声明。

### Legacy Assets

- `../ego_1`：旧 Windows desktop agent / UIA / Fleet / learning 项目。正式提交停在
  2026-02，本地有大量未提交资产和 2026-05 文档。应做只读审计后选择性迁移。
- `../egokernel`：早期 Pipeline/PID1 自主 Agent 概念。无限 heartbeat、自主 shell
  执行与当前授权/审计原则冲突，保留作历史研究。

## Why The May Position Is No Longer Enough

### 1. Local compute is becoming commodity infrastructure

Microsoft 已将 40+ TOPS NPU 作为 Copilot+ PC 的基础能力，并提供本地 NPU 开发路径；
这意味着用户现有 PC 正在获得越来越强的本地推理能力，而不是必须购买一台专用盒子。
[Microsoft Copilot+ PC developer guide](https://learn.microsoft.com/en-us/windows/ai/npu-devices/)

NVIDIA DGX Spark 与多家 OEM 的 GB10 设备已经把 128GB 统一内存、紧凑桌面形态和大型
模型本地运行推向现成产品。EgoBase 如果只强调本地算力、参数量和小机箱，会直接进入
硬件巨头的规格竞争。
[NVIDIA DGX Spark announcement](https://nvidianews.nvidia.com/news/nvidia-dgx-spark-arrives-for-worlds-ai-developers)

结论：算力路由必须是内部能力，不应是 EgoBase 的主要购买理由。

### 2. Agent connectivity is standardizing

MCP 正在成为模型连接数据与工具的通用协议，A2A 已进入 Linux Foundation，获得多家
大型厂商支持。自定义每个 connector 或把“Agent 网关”当作独占壁垒会越来越困难。
[Anthropic MCP introduction](https://www.anthropic.com/news/model-context-protocol)
[Google A2A Linux Foundation announcement](https://developers.googleblog.com/google-cloud-donates-a2a-to-linux-foundation/)

结论：Ego 应采用标准协议，把差异放在用户拥有的证据、身份、策略、长期连续性与行动
信任上。

### 3. Local home AI already has credible incumbents

Home Assistant 已提供可完全本地运行的语音路径，也能连接本地 LLM。单纯“家庭本地 AI
中枢”仍然太宽，容易与成熟家庭自动化生态正面竞争。
[Home Assistant Voice Preview Edition](https://www.home-assistant.io/voice-pe/)

结论：EgoBase 第一阶段不做通用智能家居控制器，而围绕 EgoLink 和个人长期上下文建立
独特闭环。

### 4. Wearable AI rewards concrete jobs, not abstract assistants

Meta、Xiaomi 和 Alibaba 的 AI 眼镜都依托现有生态，把功能落到拍摄、翻译、通信和场景
交互；相反，试图以新硬件替代手机的 Humane AI Pin 已停止销售和服务。
[Meta AI glasses update](https://about.fb.com/news/2025/04/meta-ai-begins-roll-out-on-ray-ban-meta-glasses-to-even-more-countries-in-the-eu/)
[Xiaomi AI Glasses](https://www.mi.com/global/discover/article?id=5172)
[Alibaba Quark AI Glasses](https://www.alibabacloud.com/blog/602717)
[Humane shutdown report](https://www.axios.com/2025/02/18/humane-ai-pin-shut-down-hp)

结论：EgoLink 当前“安全定位器”的收敛是正确的。EgoBase 也必须围绕一个具体任务，而
不是再次包装成万能私人 AI。

## Diagnosis Of The Old Position

| 问题 | 旧表现 | 后果 |
|---|---|---|
| 硬件先于任务 | RK3588、HDMI、USB HID、NPU、家庭基站并行定义 | 产品价值被规格掩盖，路线容易随芯片变化 |
| 一个名称承担过多角色 | Ego 同时是终端、Agent、Data Core、Operator、Base | 团队无法判断某项功能属于谁 |
| 首发用户过宽 | 创业者、教师、创作者、家庭、自动化爱好者同时覆盖 | 无法形成一个高频、可测量的购买理由 |
| 壁垒判断偏技术 | 本地模型、路由、OCR、图谱都被视为差异点 | 这些能力正在快速标准化或商品化 |
| 工程进度替代产品进度 | 29/31 issue 接近完成 | 容易误认为产品也接近完成 |
| 子项目没有稳定契约 | EgoLink 用 PC/VPS 模拟未来 Base | 真正接入时可能重做数据与策略边界 |

## New EgoBase Position

工作定义：

> EgoBase 是家庭与个人设备之间持续运行的私有 AI 信任中枢。它保存用户拥有的长期
> 状态和策略，接收设备的最小必要证据，选择合适算力，生成可解释建议，并在授权后
> 协调行动。

它的首发价值不是“在家运行一个大模型”，而是：

- EgoLink 离开家庭后，家庭仍拥有连续、可解释的状态；
- 原始隐私数据不需要持续上传到第三方平台；
- 家庭规则、联系人和升级策略由用户控制；
- 多个设备和模型可以替换，但长期状态与审计不丢失；
- 每次提醒和行动都能说明来自什么证据、使用了什么策略。

## Development Reset

### R0 - Product And Contract Reset (2 weeks)

- 冻结 EgoBase 专用硬件与 `EDC-024`；
- 确认第一个用户角色：设备佩戴者、照护者/家庭管理员及二者关系；
- 从 EgoLink 现有 schema 提炼 CONTRACT-001；
- 定义一个端到端 Demo 和 7 天连续运行验收；
- 明确数据最小化、离线缓存、撤销和删除策略。

出口：版本化事件/命令契约、产品 Charter、可执行验收脚本。

### R1 - Cross-device Walking Skeleton (4 weeks)

- 在现有 PC 上运行 EgoBase reference runtime；
- 接收 EgoLink 的 `device_hello`、location/safety event 和 evidence manifest；
- 建立设备身份、事件幂等、离线补传和审计；
- 提供家庭状态/事件时间线和一个明确行动建议；
- 全链路只使用真实或明确标记的 mock 数据。

出口：EgoLink -> EgoBase -> 用户确认 -> action result 的可回放闭环。

### R2 - Real-use Validation (4 weeks)

- 连续 7 天运行；
- 统计事件到达率、重复率、延迟、离线恢复和误提醒；
- 访谈/观察用户是否理解和信任提醒；
- 验证 Data Core 哪些模块真实有用，删除未服务场景的复杂度；
- 完成威胁模型、数据导出/删除和设备丢失恢复。

出口：一页产品证据报告，而不是功能列表。

### R3 - Hardware Go/No-go

只有当现有 PC reference runtime 证明持续价值后，才决定：

- 是否需要专用 EgoBase；
- 需要低功耗常开还是高算力按需唤醒；
- 存储、NPU/GPU、网络、UPS 和价格目标；
- 自研硬件、ODM、NAS app、AI PC app 或迷你主机预装哪一种形态更合理。

## Stop / Continue / Migrate

### Stop now

- 把“更多 TOPS / 更大模型”作为 EgoBase 路线；
- 在真实闭环前实现通用 Compute Fabric；
- 同时面向个人工作、家庭安全、企业协同和通用 Operator；
- 把工程 issue 完成率当成产品完成率。

### Continue

- EgoLink D2/D5 主线与诚实证据规则；
- Data Core 的 Evidence-first、Policy、Audit 和可重算 Enhancement；
- 本地优先与最小必要云增强；
- action plan、授权和验证闭环。

### Migrate selectively

- 从 `ego_1` 迁移 UIA adapter、action verification 和审批/Fleet 经验；
- 从 EgoLink 迁移稳定的事件 schema，而不是复制 Message Hub 内部实现；
- Data Core 中与首发场景无关的 Work Graph/Brief 功能先保持，不继续扩展。

## Decisions Still Required

以下是产品决策，不应由实现代码替代：

1. 第一位付费/高价值用户到底是谁；
2. 首个安全/定位场景中，谁是佩戴者，谁是接收者；
3. 中国市场的通知与联系人通道先选哪一个；
4. 哪些原始数据永不离开 EgoLink，哪些允许进入 EgoBase；
5. 7 天试用后什么行为证明用户愿意留下 EgoBase。
