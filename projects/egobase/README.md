# EgoBase

**Status:** product reset / software-first validation

**Working definition:** 家庭与个人设备之间的私有 AI 信任中枢，而不是通用“本地大模型盒子”。

## Working Product Position

EgoBase 在家庭或个人可信网络中持续运行，承担五项职责：

1. 接收 EgoLink、PC 和后续设备发送的受控事件与证据；
2. 保存用户拥有的长期数据、身份、设备关系和策略；
3. 在本地模型、AI PC、局域网算力和授权云模型之间选择运行位置；
4. 生成提醒、Brief、设备协同和行动计划；
5. 对每次数据访问、模型调用、授权和动作保留可解释审计。

算力路由是 EgoBase 的内部能力，不是产品定位。硬件形态也不是第一阶段壁垒。
EgoBase 的价值应来自跨设备连续性、可信策略、长期证据和可验证行动。

## What EgoBase Is Not

- 不是又一台 NAS；
- 不是只运行本地 LLM 的 AI 盒子；
- 不是以 TOPS、模型参数量或芯片型号定义的迷你服务器；
- 不是家庭自动化平台的简单复刻；
- 不是 EgoLink 的云端替代品；
- 不是在产品闭环验证前就确定的专用硬件 SKU。

## First Validation Wedge

第一条产品验证链以 EgoLink 为入口：

```text
随身端定位/安全事件
  -> 最小必要证据进入 EgoBase
  -> EgoBase 维护长期状态与家庭策略
  -> 生成提醒、解释或升级建议
  -> 用户确认/授权
  -> 设备或服务执行并回写结果
```

这条链必须先在现有 PC 或迷你主机上连续运行，再决定是否需要专用 EgoBase 硬件。

## Current Software Assets

`data-core/` 是已实现的 Ego Data Core v0.1，已经证明：

- 文件与截图 Evidence 入库；
- 文档解析、全文检索和 OCR enhancement；
- Work Graph、Daily Brief 和数据健康；
- 隐私策略、审计和授权后的 action dry-run；
- 本地 API、CLI、Web UI 与一键演示。

它还没有证明：

- EgoLink 到 EgoBase 的真实协议与长期运行；
- 家庭成员、设备身份、远程访问和恢复机制；
- 用户愿意持续使用的核心场景；
- 专用硬件比现有 PC/AI PC/迷你主机更有价值。

## Directory

```text
egobase/
  README.md
  data-core/        current local evidence and agent runtime prototype
  docs/             product reset and future EgoBase-specific decisions
```

Current decision document: [Product Charter](docs/PRODUCT_CHARTER.md).
