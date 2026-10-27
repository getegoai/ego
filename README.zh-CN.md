# Ego

![EgoLabs：你的 AI，你的数据，你的规则](docs/media/ego-cover.svg)

**公开构建由个人掌控的 AI。**

[English](README.md) · [EgoLabs](https://github.com/getegoai) · [getego.ai](https://getego.ai) · [路线](docs/ROADMAP.md)

我们希望让每个人拥有持续扩展认知与行动能力的 AI 伙伴，并掌控自己的数据、授权和长期上下文。我们把它称为 **AI 影子**：能够跨设备与人共同成长，帮助重要目标持续推进的系统。

当前从两个相互连接的项目开始：

| 项目 | 职责 | 当前阶段 |
|---|---|---|
| [EgoLink](https://github.com/getegoai/egolink) | 随身感知、定位、蜂窝通信与实体交互 | 工程原型；源码及原始 471 次连续研发提交已公开 |
| EgoBase | 用户控制的存储、个人上下文、策略与协同行动 | 本地软件原型；初期计划保留在本仓库 |

本仓库承载总体愿景、系统边界和跨项目路线。EgoBase 出现独立开发或发布需要时，再拆为独立仓库。

## 当前状态

**现有 [EgoBase/Data Core 实现](projects/egobase/data-core/)及其原始 34 次连续提交已纳入本仓库。** 既有公开定义、路线与[官网源码](website/)继续保留；本次导入未修改网站文件。

项目在公开启动前已有研发。现有 Data Core 原型支持本地证据存储、文档处理、检索、每日简报、策略、审计与授权后的行动演练；EgoLink 已有独立硬件和固件工作。EgoLink 到 EgoBase 的完整产品闭环尚未完成验证。

![产品方向示意：EgoLink 物理观察、个人掌控的 EgoBase 与有证据支持的决定](docs/media/system/ego-system.svg)

*产品方向概念图。EgoLink 仍为工程原型，Data Core 是运行在 PC 上的软件原型，
完整连接仍在研发中。*

本地控制是设计方向，不表示当前所有组件已在本地运行，也不表示隐私和可靠性已完成验证。

### 当前软件界面

![Data Core 真实本地界面，运行仓库自带的合成演示工作区](docs/media/screenshots/data-core-workspace.png)

*现有 Data Core 应用的真实截图，使用项目自带的合成演示文件。
[图片导览](docs/VISUAL_TOUR.md)还包含证据检索、实物照片、图片来源与可直接取用的宣传配图。*

## 接下来

- 继续开发已导入的 EgoBase/Data Core 实现及已有测试。
- 在 [EgoLink 公开仓库](https://github.com/getegoai/egolink)继续固件、服务、硬件与工具研发；[历史与节点](https://github.com/getegoai/egolink/blob/main/docs/HISTORY.md)可直接查阅。
- 在 PC 上打通版本化 EgoLink 事件、用户控制的存储、回放和小范围策略/行动闭环。
- 通过公开提交、Issue 和 PR 持续开发，如实呈现未完成工作和已知失败。

具体导入任务和近期方向见[路线](docs/ROADMAP.md)。

## 运行 Data Core

需要 Python 3.11 或更新版本。在 `projects/egobase/data-core/` 下创建并激活虚拟环境，然后运行：

```sh
python -m pip install -e ".[dev]"
python scripts/run_demo.py
python -m pytest
```

安装、API、CLI、本地界面和数据位置见[组件说明](projects/egobase/data-core/README.md)。示例运行用于检查实际实现，本仓库继续承载产品研发。

[历史索引](docs/HISTORY.md)记录原始提交、迁移边界和关键节点。保留旧版本是为了呈现研发过程，不表示所有旧版本都已在当前依赖环境重新验证。

## 参与

欢迎讨论使用场景、质疑接口、报告问题、改进文档和贡献实现。我们一起建设实际系统。可以从 [Issue](https://github.com/getegoai/ego/issues) 或[贡献说明](CONTRIBUTING.md)开始。

## 许可

原创文档采用 **CC BY 4.0**，见 [LICENSE](LICENSE)。[官网实现](website/)采用 **Apache-2.0**，见 [website/LICENSE](website/LICENSE)。本次导入的原创 Data Core 源码、测试、契约、配置和示例数据采用 **Apache-2.0**，见 [Data Core LICENSE](projects/egobase/data-core/LICENSE)；说明文档仍采用 CC BY 4.0。依赖边界见[第三方说明](THIRD_PARTY_NOTICES.md)。硬件、模型、数据和第三方材料分别说明适用许可。
