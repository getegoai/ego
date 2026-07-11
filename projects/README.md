# Ego Project Registry

Ego 采用联邦式多仓库组织：总项目统一产品边界、跨项目契约和路线图；具备独立
硬件、发布节奏或部署面的子项目保留自己的 Git 仓库。

| 项目 | 当前状态 | 代码位置 | 说明 |
|---|---|---|---|
| EgoBase | Product reset | `projects/egobase/` | 本仓库管理；当前已有 Data Core 软件原型，独立硬件尚未重新定义 |
| EgoLink | Active engineering alpha | sibling `../egolink` checkout | 独立仓库；随身安全定位与感知节点，当前主线为 D2 定位基线和 D5 数据飞轮 |
| Ego Operator / Desktop Agent | Legacy review | sibling `../ego_1` checkout | 旧 Windows Agent、UIA、Fleet 和学习循环资产；工作区有未提交改动，不移动、不覆盖 |
| Ego Kernel Pipeline | Archived concept | sibling `../egokernel` checkout | 仅有早期 Pipeline/PID1 概念文档，不作为当前产品主线 |

## Repository Rules

1. 子项目必须有单一产品职责、独立状态页和可验证里程碑。
2. 跨项目只共享版本化契约，不直接依赖对方内部数据库或运行目录。
3. 活跃独立仓库不复制进本仓库；后续需要统一构建时再选择 submodule 或发布包。
4. 遗留项目先做资产清单与迁移决策，不直接合并代码。
5. Ego 总项目的路线优先于子项目的功能堆叠，但不得覆盖子项目已验证的工程事实。
