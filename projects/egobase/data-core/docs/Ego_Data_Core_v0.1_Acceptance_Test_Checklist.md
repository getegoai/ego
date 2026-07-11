# Ego Data Core v0.1 验收测试清单

**版本**：v0.1  
**日期**：2026-05-28

## 1. 基础验收

- [ ] 本地 API 可启动。
- [ ] `/api/v1/health` 返回 ok。
- [ ] SQLite schema 初始化成功。
- [ ] pytest 在干净环境通过。
- [ ] 所有测试使用临时 `EGO_DATA_HOME`。

## 2. 数据安全验收

- [ ] 扫描器只读访问用户目录。
- [ ] 系统不会移动、删除、重命名用户文件。
- [ ] Vault 文件名不暴露用户完整绝对路径。
- [ ] sensitive/critical 数据默认不能发外部模型。
- [ ] action 未授权前不能 execute。

## 3. Evidence-first 验收

- [ ] 每个 raw_object 至少有一个 version。
- [ ] 每个 version 有 hash。
- [ ] 每个关键 evidence 有 source、raw_object、version 或合理例外。
- [ ] 每个 enhancement 有 evidence link。
- [ ] Daily Brief 中事实条目有 evidence reference。

## 4. Enhancement 验收

- [ ] summary/tag 可生成。
- [ ] RuleBasedAdapter 在无外部模型时可运行。
- [ ] Ollama 不可用时系统不崩溃。
- [ ] 模型调用有 model_invocation 记录。
- [ ] enhancement 可标记 verified/rejected/superseded。

## 5. Work Graph 验收

- [ ] Project candidate 可生成。
- [ ] Task/Question/Risk candidate 可生成。
- [ ] 用户可确认/驳回。
- [ ] 被驳回候选不会在无变化时反复出现。

## 6. Brief 验收

- [ ] Daily Brief 可按日期生成。
- [ ] Brief 可导出 Markdown。
- [ ] Brief 包含 Data Health。
- [ ] 没有足够数据时，Brief 不编造内容。
- [ ] 用户反馈可记录。

## 7. Demo 验收

- [ ] `scripts/run_demo.sh` 可在干净环境跑通。
- [ ] Demo 全程不需要云端模型。
- [ ] Demo 生成一个 Markdown Brief。
- [ ] Demo 展示至少一个自动化机会 dry-run。
- [ ] Demo 展示 Audit Log。

## 8. 版本完成标准

全部 P0 Issue 完成，P1 Issue 中至少完成：

- EDC-012 OllamaAdapter 或明确跳过；
- EDC-014 Project Discovery；
- EDC-015 Task/Question/Risk；
- EDC-019 UI 或 EDC-025 CLI 至少一个完整入口；
- EDC-021 Action dry-run；
- EDC-026 一键 Demo。
