# Ego roadmap / Ego 路线

This is a working direction, not a delivery schedule. Implementation status belongs in the relevant issues and code. / 本文记录工作方向，不承诺交付日期；具体进展在对应 Issue 和代码中持续更新。

| Horizon | Work / 工作 |
|---|---|
| **Now / 现在** | Continue Data Core and EgoLink development from their imported source and continuous history. / 当前源码与连续历史已导入，在各公开仓库继续 Data Core 与 EgoLink 的真实研发。 |
| **Next / 接下来** | Connect EgoLink events to a PC-hosted EgoBase: store, replay, apply a small policy, and record a user decision and action result. / 在 PC 上打通 EgoLink 事件接收、保存、回放、简单策略、用户决定和行动结果记录。 |
| **Later / 更远期** | Extend long-term personal context, authorized actions, and coordination across devices. Evaluate dedicated hardware through actual use. / 扩展个人长期上下文、授权行动和跨设备协作，根据实际使用评估专用硬件。 |

## Initial implementation import / 首批实现导入

- [x] Bring the existing Data Core into `projects/egobase/data-core/`: local evidence storage, parsing/search, briefs, policy/audit, API, CLI, and web UI. / 导入现有本地数据底座及接口。
- [x] Include existing tests, dependencies, configuration examples, and run instructions; state which commands were checked on the imported version. / 同步已有测试、依赖、配置示例与运行说明，注明实际验证范围。
- [x] Link the [actual EgoLink implementation](https://github.com/getegoai/egolink) and [retained history](https://github.com/getegoai/egolink/blob/main/docs/HISTORY.md). / 关联 EgoLink 真实实现及保留的连续历史。
- [ ] Implement the [first Link-to-Base integration task](https://github.com/getegoai/ego/issues/2): versioned observation/evidence events, idempotent ingestion, and replay. Reuse existing schemas rather than building another generic platform. / 推进已建立的版本化事件、幂等接入和回放任务，复用已有契约。

## First connected outcome / 第一条跨设备结果

An event from EgoLink should retain its source and time in user-controlled storage, be understandable in replay, and support a small user-authorized workflow with a recorded result. Missing data, repeated events, and interrupted connections should remain visible. / EgoLink 事件进入用户控制的存储后应保留来源与时间、支持回放，并推动一项经用户授权且有结果记录的工作；缺失、重复和断连不能被隐藏。

The complete connected outcome is not yet validated. EgoBase remains a software workspace here; splitting a repository or designing dedicated hardware is not a prerequisite for the next implementation step. / 该完整闭环尚未验证。EgoBase 先保留为本仓库的软件工作区，拆库和专用硬件设计不作为下一步实现的前置。
