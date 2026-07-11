# Project Ego

Ego 是一个面向个人长期使用的私有 AI 系统项目，而不是单一硬件、单一模型或单一应用。

当前总项目正在进行产品边界重置。新的组织原则是：

- `EgoLink` 负责随身感知、定位、安全交互和低功耗事件入口；
- `EgoBase` 负责家庭/本地可信运行、长期状态、策略、设备协同和算力调度；
- `Ego Data Core` 是 EgoBase 可复用的软件底座之一，负责 Evidence、Enhancement、Work Graph、Brief、Policy 和 Audit；
- `Ego Operator` 是跨项目的受控行动能力，不再单独代表整个 Ego 产品；
- 云端只作为可选增强、远程中继和设备服务，不作为用户数据与身份的唯一控制者。

## Repository Role

这个仓库现在承担 Ego 总项目的组合管理与 EgoBase 工作区职责：

```text
ego/
  docs/                         总项目定位、路线与状态
  projects/
    egobase/                    EgoBase 产品与软件工作区
      data-core/                已实现的 Ego Data Core v0.1
    egolink/                    外部独立仓库的登记入口
    legacy/                     旧 Agent / Kernel 资产登记
```

EgoLink 仍保留在独立仓库中，以避免破坏其活跃开发历史和发布流程。详见
[项目登记](projects/README.md)。

## Current Direction

当前优先级不是继续堆叠 EgoBase 硬件规格，而是先证明一个跨设备产品闭环：

```text
EgoLink 产生受控事件与证据
  -> EgoBase 接收并保留长期状态
  -> 本地策略判断与模型增强
  -> 用户收到有价值的提醒、解释或行动建议
  -> 用户授权后执行并形成审计
```

在这个闭环被真实用户连续使用前，EgoBase 以现有 PC/迷你主机作为参考运行环境，
不启动专用硬件量产定义。

## Start Here

- [总项目产品组合](docs/PRODUCT_PORTFOLIO.md)
- [2026-07 重新定位分析](docs/REPOSITIONING_2026-07.md)
- [总项目开发状态](docs/DEVELOPMENT_STATUS.md)
- [EgoBase 工作区](projects/egobase/README.md)
- [Ego Data Core](projects/egobase/data-core/README.md)

运行现有 Data Core：

```powershell
cd projects\egobase\data-core
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python scripts\run_demo.py
```
