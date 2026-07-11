# Legacy Project Registry

这些目录位于当前仓库之外，仅作为待审计资产来源，不是当前产品主线。

## `../ego_1`

旧 Windows desktop agent / Operator 原型，包含 UIA、OCR、微信 pack、Fleet、
观察学习和授权执行等代码。最后正式 commit 在 2026-02，但本地有大量未提交改动，
部分文档更新到 2026-05。未经单独审计不得搬迁、清理或覆盖。

潜在可迁移资产：

- autonomy policy gate；
- UIA/视觉操作 adapter；
- action verification；
- Fleet 配置与审批工具；
- trajectory/learning 报告。

## `../egokernel`

只有一份早期 Pipeline/PID1 自主 Agent 概念文档。它提出的无限 heartbeat、shell
执行和自我演化路线与当前“有边界、可授权、可审计”的产品原则冲突，保留作历史
研究，不进入当前开发计划。
