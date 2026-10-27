# Ego Development Status

> Historical July 2026 project record. Preserve its dated statements as development history; current public scope and next work are in [README](../README.md), [ROADMAP](ROADMAP.md), and the [history index](HISTORY.md).
**Updated:** 2026-07-12

**Program phase:** Portfolio reset / EgoBase product reset

**Branch:** `main`

## Executive Status

仓库已从单一 Data Core 项目重组为 Ego 总项目工作区。当前没有理由继续按旧任务书直接
实现 `EDC-024 Compute Fabric`；下一步必须先完成 EgoLink 与 EgoBase 的产品/契约闭环。

| Area | Status | Evidence |
|---|---|---|
| Ego portfolio boundary | Working baseline | 根 README、产品组合与项目登记已建立 |
| EgoBase positioning | Draft, needs validation | 已从“算力路由基站”调整为“私有 AI 信任中枢”工作假设 |
| Ego Data Core engineering | 29/31 planned issues complete | 2026-07-12 搬迁前后均为 135 tests passed |
| Ego Data Core product validation | Not demonstrated | 尚无 EgoLink 接入、长期家庭使用或专用硬件价值证据 |
| EgoLink | Active external project | 2026-07-11 状态；`v0.1.0` Engineering Alpha；D2/D5 主线 |
| EgoLink -> EgoBase contract | Not started | EgoLink 有局部 schema，尚未形成跨仓库正式版本 |
| EgoBase dedicated hardware | Paused | 等待软件闭环与真实使用证据 |
| Legacy Operator/Fleet assets | Inventory only | `../ego_1` 工作区脏，禁止直接移动或覆盖 |
| Ego umbrella remote | Missing | 当前仓库没有 Git remote；完成重定位后应建立私有远程 |

## Progress Interpretation

- Data Core 工程任务完成率：`29 / 31`，约 `94%`；
- Data Core 技术闭环：完成；
- EgoBase 独立产品定义：工作假设已建立，未验证；
- EgoLink 到 EgoBase 真实闭环：`0` 个已验收连续运行；
- EgoBase 专用硬件：未进入定义阶段。

因此，不能把 `94%` 理解为 EgoBase 产品完成度。它只说明一套可复用软件底座已经成熟
到可以进入真实产品验证。

## Active Work Package

### EGO-R0 - Product And Contract Reset

目标：在不开发新硬件的前提下，定义并跑通第一条 EgoLink -> EgoBase 产品闭环。

1. `EGO-R0-001`：确认首发用户、任务和 7 天验收标准；
2. `CONTRACT-001`：统一 device hello、observation、evidence、safety event、command、result；
3. `BASE-001`：Data Core 接收 EgoLink 事件的幂等入口；
4. `DEMO-001`：EgoLink event -> EgoBase policy -> user decision -> result/audit；
5. `PILOT-001`：连续 7 天 reference runtime 证据。

## Frozen Work

- `EDC-012 OllamaAdapter`：除非 DEMO-001 明确需要，不做；
- `EDC-024 Compute Fabric`：产品/契约重置前暂停；
- EgoBase 专用板卡、外壳和量产规格：R3 再决策；
- 通用家庭自动化、企业多人系统和公网算力网络：不进入近期计划；
- `ego_1` 全量合并：必须先做只读迁移审计。

## Verification

- 重组前：`135 passed, 1 warning`；
- 重组后从 `projects/egobase/data-core` 运行：`135 passed, 1 warning`；
- 警告来自 Starlette TestClient 的 httpx 兼容弃用提示，不是本次重组回归。

## Latest Commits

- `18f9d89 chore: reorganize ego as multi-project workspace`
- `53f3691 EDC-023: add screenshot OCR enhancements`
- `66edd3d EDC-022: add manual screenshot capture`
