# Ego Data Core v0.1 技术架构与数据库 Schema

**版本**：v0.1 内部工程稿  
**日期**：2026-05-28  
**项目代号**：Ego / ShadowNode  
**对应文档**：《Ego Data Core v0.1 产品定义》  
**文档性质**：技术架构、数据库 Schema、API 草案、任务调度与安全审计规范  
**目标读者**：Ego 项目负责人、后端开发、数据工程、Agent 工程、前端开发、硬件/Operator 组

---

## 0. 本文档的作用

本文档把《Ego Data Core v0.1 产品定义》进一步落到工程实现层。

它回答六个问题：

1. Ego Data Core v0.1 的系统边界是什么；
2. 模块之间如何分工；
3. 原始证据、增强数据、项目、任务、简报、审计如何建模；
4. 第一版数据库表如何设计；
5. 后端 API 如何设计；
6. 如何保证本地优先、证据优先、模型可替换、行动可审计。

本文档不是最终架构，而是 **v0.1 可开工版本**。原则是：

> 先把“采集—保存—增强—追溯—汇报”的最小闭环跑通，再逐步接入 Ego Operator、Ego Compute Fabric、Ego Sense Kit 和专用硬件。

---

## 1. 架构总原则

### 1.1 三条不可违反的技术原则

#### 原则一：Original Evidence is Truth

Ego 系统内，原始证据是最高事实层。

- 文件原件、截图、网页快照、操作日志、音视频片段等属于 Evidence Layer；
- 摘要、标签、OCR、图谱、任务、风险、问题都只是 Enhancement Layer；
- Enhancement 可以被替换、重算、驳回、升级；
- Evidence 不得被模型输出覆盖；
- 任何关键结论必须能追溯到至少一个 Evidence。

#### 原则二：Enhanced Data is Recomputable

增强数据是可重算的解释层。

- 同一份 Evidence 可以被不同模型、多次生成不同 Enhancement；
- Enhancement 必须记录模型、Prompt 版本、运行时、时间、置信度、证据来源；
- 当模型升级时，允许重新生成新的 Enhancement，并将旧版本标记为 `superseded`；
- 用户确认过的 Enhancement 标记为 `verified`，但仍不覆盖 Evidence。

#### 原则三：Local Ego Kernel Controls Everything

外部算力可以参与计算，但不能控制 Ego。

- 完整 Vault 不直接暴露给外部模型；
- 外部模型只能获得本地生成的最小必要上下文；
- 外部模型没有文件系统权限、设备权限、执行权限；
- 所有模型调用、动作建议、用户授权、执行步骤必须写入审计日志；
- 最终动作由本地 Ego Kernel 或用户确认后执行。

---

## 2. v0.1 系统边界

### 2.1 v0.1 必须实现的闭环

```text
用户授权数据源
  ↓
Source Connector 监控文件/屏幕/网页/事件
  ↓
Raw Object 入库
  ↓
Evidence 建立证据索引
  ↓
Night Shift 创建增强任务
  ↓
Model Router 选择本地/外部模型
  ↓
Ego Twin 生成 Enhancement
  ↓
Work Graph 生成 Project / Task / Question / Risk / Automation
  ↓
Ego Brief 生成 Daily Brief
  ↓
用户确认、驳回、授权
  ↓
Audit Log 记录全过程
```

### 2.2 v0.1 只做三类数据源

| 数据源 | v0.1 范围 | 暂不做 |
|---|---|---|
| 文件系统 | 指定目录、常见文档格式、文件版本、元数据 | 全盘扫描、系统目录、聊天软件数据库破解 |
| 屏幕状态 | 手动/定时/事件触发截图、活跃窗口、OCR | 全天候录屏、隐私应用全量采集 |
| 网页快照 | 用户主动保存或浏览器插件传入的页面 | 全浏览历史监听、账号 Cookie 抓取 |

### 2.3 v0.1 的第一目标

> 每天自动生成一份有证据支撑的 Ego Daily Brief，让用户看到 Ego 已经理解了其文件、项目、任务和未决问题。

---

## 3. 总体系统架构

### 3.1 模块图

```text
┌──────────────────────────────────────────────────────────────┐
│                        Local Web UI                           │
│  Brief / Project / Evidence / Search / Authorization / Audit   │
└──────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                        Local API                              │
│                 FastAPI / Localhost-first API                 │
└──────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                      Ego Kernel                               │
│  Safety Kernel · Policy Engine · Audit · Identity · Config     │
└──────────────────────────────────────────────────────────────┘
       │             │              │             │
       ▼             ▼              ▼             ▼
┌───────────┐ ┌─────────────┐ ┌────────────┐ ┌───────────────┐
│ Connectors│ │ Ego Vault   │ │ Ego Twin   │ │ Work Graph     │
│ FS/Screen │ │ Evidence DB │ │ Enhance DB │ │ Project/Task   │
└───────────┘ └─────────────┘ └────────────┘ └───────────────┘
       │             │              │             │
       ▼             ▼              ▼             ▼
┌──────────────────────────────────────────────────────────────┐
│                    Ego Night Shift                            │
│      Job Queue · Scheduler · Retry · Priority · Backoff        │
└──────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│             Model Router + Compute Fabric                     │
│  Local Model · PC · Ego Node · LAN Server · External Model     │
└──────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                    Operator Bridge                            │
│     Plan · Authorize · Execute · Verify · Rollback · Audit     │
└──────────────────────────────────────────────────────────────┘
```

### 3.2 模块职责表

| 模块 | 职责 | v0.1 必须程度 |
|---|---|---|
| Local API | 提供本地 REST API | P0 |
| Local Web UI | 展示 Brief、Evidence、Project、Audit | P0/P1 |
| Safety Kernel | 授权、隐私等级、外部调用策略、高风险动作控制 | P0 |
| Connectors | 文件、屏幕、网页数据接入 | P0 |
| Ego Vault | 原始证据与元数据保存 | P0 |
| Ego Twin | 增强数据保存与版本管理 | P0 |
| Work Graph | Project / Task / Question / Risk / Automation 关系建模 | P1 |
| Night Shift | 后台任务队列与调度 | P0/P1 |
| Model Router | 选择模型、记录调用 | P0 |
| Compute Fabric | 选择本机、本地服务器、外部模型 | P1 |
| Brief Engine | 生成 Daily Brief / Project Brief | P0 |
| Operator Bridge | 预留物理操作接口 | P1 |
| Audit | 记录采集、处理、调用、授权、执行 | P0 |

---

## 4. 数据分层设计

### 4.1 数据层级

```text
Layer 0: Source
  数据来源，如目录、屏幕、网页、设备。

Layer 1: Raw Object
  原始对象，如某个文件、某张截图、某个网页快照。

Layer 2: Object Version
  原始对象的具体版本，如文件 v1/v2、截图某次采集。

Layer 3: Evidence
  可引用的证据单元，可指向整个文件、文件段落、截图区域、网页正文、操作日志片段。

Layer 4: Enhancement
  模型或规则基于 Evidence 生成的增强数据，如摘要、OCR、标签、实体、任务、风险。

Layer 5: Work Graph
  项目、任务、问题、风险、自动化机会等工作对象。

Layer 6: Report / Brief
  面向用户的主动汇报。

Layer 7: Action / Operator
  建议动作、授权动作、执行步骤和核验结果。
```

### 4.2 为什么要区分 Raw Object、Version、Evidence

v0.1 中，很多系统会犯一个错误：把“文件”直接当成“证据”。这会导致无法处理版本、片段、截图区域、网页快照等问题。

正确区分如下：

| 概念 | 示例 | 作用 |
|---|---|---|
| Raw Object | `/docs/Ego方案.docx` 这个文件对象 | 标识对象本身 |
| Object Version | 2026-05-28 10:00 的文件版本 | 标识某个时间点的内容 |
| Evidence | 文件第 3 页第 2 段，或截图中的一个区域 | 支撑具体结论 |
| Enhancement | “该段说明了 Ego 的商业模式” | 模型解释 |

这样设计后，系统可以回答：

> 这个结论到底来自哪个文件、哪个版本、哪个段落、哪个截图区域？

这就是 Ego 的证据优先架构。

---

## 5. ID 规范

所有主键使用字符串 ID，不依赖自增整数。这样便于本地设备、未来多节点同步和离线生成。

### 5.1 ID 前缀

| 对象 | ID 前缀 | 示例 |
|---|---|---|
| User | `usr_` | `usr_local_001` |
| Device | `dev_` | `dev_ego_node_s_001` |
| Source | `src_` | `src_docs_20260528_001` |
| Raw Object | `obj_` | `obj_file_01hx...` |
| Object Version | `ver_` | `ver_01hx...` |
| Evidence | `ev_` | `ev_20260528_000001` |
| Text Chunk | `chk_` | `chk_20260528_000001` |
| Enhancement | `enh_` | `enh_20260528_000001` |
| Project | `proj_` | `proj_ego_data_core` |
| Task | `task_` | `task_20260528_000001` |
| Question | `q_` | `q_20260528_000001` |
| Risk | `risk_` | `risk_20260528_000001` |
| Automation | `auto_` | `auto_20260528_000001` |
| Report | `brief_` | `brief_daily_20260528` |
| Job | `job_` | `job_20260528_000001` |
| Model Invocation | `mi_` | `mi_20260528_000001` |
| Action | `act_` | `act_20260528_000001` |
| Audit | `aud_` | `aud_20260528_000001` |

### 5.2 ID 生成建议

v0.1 可采用：

```text
<prefix><YYYYMMDD>_<random_base32_or_ulid>
```

例如：

```text
ev_20260528_01J0K4AHM8Y1M6S9FQ9
```

长期建议采用 ULID 或 UUIDv7，便于按时间排序。

---

## 6. 数据库存储策略

### 6.1 v0.1 推荐组合

| 数据类型 | 存储建议 | 说明 |
|---|---|---|
| 元数据 | SQLite 优先，未来 PostgreSQL | v0.1 单用户本地部署足够 |
| 原始文件 | 文件系统对象存储 | 不建议把大文件塞入数据库 |
| 截图/快照 | 文件系统对象存储 | DB 存路径、hash、bbox、索引 |
| 长文本 | 文件系统 + text_chunks 索引 | 便于重建和重新切块 |
| 向量 | LanceDB / Qdrant | SQLite 仅存 embedding 引用 |
| 审计日志 | append-only JSONL + DB 索引 | 防止被模型或逻辑误改 |
| 配置 | YAML + DB | 敏感密钥不明文入库 |

### 6.2 本地目录结构

```text
~/.ego/
  config/
    ego.yaml
    policies.yaml
  vault/
    objects/
      documents/
      images/
      screenshots/
      web_snapshots/
      events/
    versions/
    extracted_text/
    thumbnails/
  db/
    ego_data_core.sqlite
  vector/
    lancedb/
  audit/
    audit-2026-05.jsonl
  jobs/
    queue_state/
  cache/
    model_outputs/
    temp/
  exports/
  backups/
```

### 6.3 数据库实现选择

v0.1 建议采用 SQLite-first：

- 原因：本地部署简单、跨平台、无需服务器；
- JSON 字段用 TEXT 存储，应用层保证 JSON 合法；
- 后续迁移 PostgreSQL 时，TEXT JSON 字段可迁移为 JSONB；
- 向量不存 SQLite 主库，只存向量库引用。

---

## 7. 数据库 Schema 总览

### 7.1 表分组

| 分组 | 表 |
|---|---|
| Identity | users, devices |
| Source & Vault | sources, raw_objects, object_versions, evidence, evidence_text_chunks |
| Enhancement | enhancements, enhancement_evidence_links, entities, entity_mentions, embeddings |
| Work Graph | projects, project_links, tasks, questions, risks, automations, graph_edges |
| Brief | reports, report_items, report_item_evidence_links |
| Runtime | jobs, job_dependencies, model_providers, models, model_invocations, compute_nodes, compute_runs |
| Operator | actions, action_steps, authorizations |
| Safety & Audit | policies, privacy_overrides, audit_logs |

### 7.2 状态枚举

#### privacy_level

```text
public | private | sensitive | critical
```

#### enhancement_status

```text
draft | verified | rejected | superseded | error
```

#### job_status

```text
pending | running | succeeded | failed | cancelled | blocked
```

#### report_type

```text
daily | weekly | project | data_health | automation
```

#### action_status

```text
proposed | authorized | running | succeeded | failed | cancelled | rejected
```

---

## 8. 核心表设计

> 完整 SQLite DDL 已单独输出为 `ego_data_core_v0_1_schema.sqlite.sql`。本节解释每张表的语义。

### 8.1 users

v0.1 先按单用户设计，但保留 user_id。

关键字段：

| 字段 | 说明 |
|---|---|
| user_id | 用户 ID |
| display_name | 显示名 |
| timezone | 时区 |
| locale | 语言地区 |
| created_at | 创建时间 |

---

### 8.2 devices

记录 Ego Node、本地 PC、服务器、未来感知套件。

关键字段：

| 字段 | 说明 |
|---|---|
| device_id | 设备 ID |
| device_type | pc / ego_node / server / sensor / phone |
| hostname | 主机名 |
| os | 操作系统 |
| capabilities_json | CPU/GPU/NPU/内存/屏幕采集/Operator 能力 |
| trust_level | local / trusted_lan / external |

---

### 8.3 sources

数据来源。用户必须明确授权 Source。

示例：

- 一个文件夹；
- 一个截图采集通道；
- 一个网页保存插件；
- 一个 Operator 日志源；
- 未来一个麦克风或摄像头。

关键字段：

| 字段 | 说明 |
|---|---|
| source_id | 数据源 ID |
| source_type | filesystem / screen / browser / operator / sensor |
| root_uri | 目录或采集入口 |
| enabled | 是否启用 |
| privacy_level | 默认隐私等级 |
| scan_policy_json | 扫描策略 |
| retention_policy_json | 保留策略 |

---

### 8.4 raw_objects

原始对象，不等于证据。一个文件、一张截图、一个网页快照都是 Raw Object。

关键字段：

| 字段 | 说明 |
|---|---|
| raw_object_id | 原始对象 ID |
| source_id | 来自哪个 Source |
| object_type | file / screenshot / web_snapshot / event / operator_log |
| original_uri | 原路径或原 URI |
| canonical_uri | Ego Vault 中的保存路径 |
| content_hash | 当前内容 hash |
| mime_type | MIME 类型 |
| current_version_id | 当前版本 |
| privacy_level | 对象隐私等级 |

---

### 8.5 object_versions

原始对象的版本。文件修改后新增版本，不覆盖旧版本。

关键字段：

| 字段 | 说明 |
|---|---|
| version_id | 版本 ID |
| raw_object_id | 对应 Raw Object |
| version_no | 版本号 |
| storage_uri | Vault 中版本文件路径 |
| content_hash | 版本 hash |
| extracted_text_uri | 解析出的文本路径 |
| captured_at | 采集时间 |

---

### 8.6 evidence

可引用证据。Evidence 可以指向整个文件版本，也可以指向某个片段。

关键字段：

| 字段 | 说明 |
|---|---|
| evidence_id | 证据 ID |
| raw_object_id | 对应 Raw Object |
| version_id | 对应版本 |
| evidence_type | document / screenshot / text_span / image_region / web_snapshot / event |
| evidence_uri | 证据文件路径 |
| evidence_selector_json | 页码、bbox、时间段、字符范围等 selector |
| content_hash | 证据 hash |
| privacy_level | 证据隐私等级 |
| retention_policy | keep / rolling / manual_review |

---

### 8.7 evidence_text_chunks

文本切块索引，用于搜索、RAG、Brief 证据引用。

注意：chunk 是索引，不是原始记忆替代物。

关键字段：

| 字段 | 说明 |
|---|---|
| chunk_id | 文本块 ID |
| evidence_id | 来源 Evidence |
| chunk_index | 块序号 |
| text | 文本 |
| token_count | token 数估计 |
| page_no | 页码 |
| char_start / char_end | 原文字符范围 |
| bbox_json | 截图或 PDF 区域 |

---

### 8.8 enhancements

增强数据主表。

关键字段：

| 字段 | 说明 |
|---|---|
| enhancement_id | 增强 ID |
| enhancement_type | summary / ocr / tag / entity / task / risk / question / project_link |
| status | draft / verified / rejected / superseded / error |
| content_json | 增强内容 |
| confidence | 置信度 |
| model_id | 使用模型 |
| model_runtime | ollama / llama_cpp / vllm / rknn / external / rule |
| prompt_hash | Prompt 版本 hash |
| generated_at | 生成时间 |
| supersedes_id | 替代哪个旧增强 |

---

### 8.9 enhancement_evidence_links

增强数据与证据的多对多关系。

一条 Enhancement 可以由多个 Evidence 支撑；一个 Evidence 可以生成多个 Enhancement。

关键字段：

| 字段 | 说明 |
|---|---|
| enhancement_id | 增强 ID |
| evidence_id | 证据 ID |
| weight | 关联权重 |
| trace_note | 追溯说明 |

---

### 8.10 projects

项目空间。v0.1 可由用户创建，也可由 Ego 自动发现。

关键字段：

| 字段 | 说明 |
|---|---|
| project_id | 项目 ID |
| name | 项目名称 |
| status | active / paused / completed / archived |
| summary | 项目摘要 |
| confidence | 自动发现置信度 |
| user_confirmed | 用户是否确认 |

---

### 8.11 tasks / questions / risks / automations

四类主动工作对象。

| 对象 | 作用 |
|---|---|
| Task | 待办、承诺、下一步动作 |
| Question | 值得用户思考或决策的问题 |
| Risk | 风险、冲突、缺口、过期事项 |
| Automation | 可自动化流程或低风险执行机会 |

这四类对象都必须能追溯 Evidence 或 Enhancement。

---

### 8.12 reports / report_items

Brief 系统。

- `reports`：一份 Daily Brief / Weekly Brief / Project Brief；
- `report_items`：简报中的每一条结论、建议、问题、风险；
- `report_item_evidence_links`：每条简报项的证据追溯。

原则：

> 简报里每一条重要结论都必须至少关联一个 Evidence 或 Enhancement。

---

### 8.13 jobs

Night Shift 后台任务。

任务类型示例：

- ingest_file；
- parse_document；
- extract_text；
- run_ocr；
- generate_summary；
- classify_project；
- extract_task；
- detect_risk；
- generate_daily_brief；
- discover_automation；
- model_eval。

v0.1 可用简单 DB 队列，后续再切 Celery/Dramatiq。

---

### 8.14 model_invocations

每次模型调用必须记录。

关键字段：

| 字段 | 说明 |
|---|---|
| invocation_id | 调用 ID |
| model_id | 模型 ID |
| job_id | 对应任务 |
| purpose | 调用目的 |
| input_ref_uri | 输入引用，敏感内容不直接明文入库 |
| output_ref_uri | 输出引用 |
| prompt_hash | Prompt 版本 |
| input_tokens / output_tokens | token 统计 |
| cost_estimate | 费用估计 |
| latency_ms | 耗时 |
| privacy_level | 调用隐私等级 |
| external_call | 是否外部调用 |
| allowed_by_policy | 是否被策略允许 |

---

### 8.15 actions / action_steps / authorizations

为 Ego Operator 预留。

v0.1 不要求完整物理操作，但要能表达：

- Ego 提出了一个动作；
- 用户授权；
- Ego 执行若干步骤；
- 每步有截图/日志证据；
- 成功或失败；
- 可回滚或不可回滚。

---

### 8.16 audit_logs

审计日志是 append-only。

记录：

- 数据源授权；
- 文件入库；
- 证据生成；
- 增强生成；
- 外部模型调用；
- 用户确认；
- 动作授权；
- 操作执行；
- 配置修改；
- 删除/导出数据。

原则：

> 模型不能修改审计日志。应用也不应 UPDATE 审计日志，只能 INSERT 新记录。

---

## 9. 关键数据结构 JSON 规范

### 9.1 evidence_selector_json

用于描述 Evidence 指向 Raw Object 的哪个区域。

#### 文档段落

```json
{
  "kind": "text_span",
  "page_no": 3,
  "char_start": 1200,
  "char_end": 1800,
  "heading_path": ["5. 产品核心架构", "5.2 Ego Twin"]
}
```

#### 截图区域

```json
{
  "kind": "image_region",
  "bbox": {"x": 128, "y": 240, "w": 760, "h": 420},
  "screen_size": {"w": 1920, "h": 1080},
  "active_window": "Microsoft Word"
}
```

#### 音视频片段，未来预留

```json
{
  "kind": "time_segment",
  "start_ms": 12500,
  "end_ms": 45100,
  "speaker": "unknown"
}
```

---

### 9.2 enhancement.content_json

#### summary

```json
{
  "title": "Ego Data Core 产品定义摘要",
  "summary": "该文档定义了 Ego Data Core 的本地数据操作系统定位。",
  "key_points": [
    "原始数据完整保留",
    "增强数据持续生成",
    "Daily Brief 是 v0.1 主交互"
  ],
  "limitations": ["未包含最终数据库 Schema"]
}
```

#### ocr

```json
{
  "language": "zh-CN",
  "text": "Ego Data Core 是一个本地优先...",
  "blocks": [
    {"text": "Ego Data Core", "bbox": [120, 80, 420, 120], "confidence": 0.96}
  ]
}
```

#### task

```json
{
  "title": "补充数据库 Schema",
  "description": "产品定义文档中已有数据结构草案，需要形成可执行 DDL。",
  "priority": "high",
  "due_date": null,
  "assignee": "user",
  "suggested_next_action": "生成 schema.sqlite.sql"
}
```

#### risk

```json
{
  "title": "采集范围过宽",
  "risk_level": "medium",
  "description": "如果 v0.1 同时接 PC、手机和传感器，开发范围会失控。",
  "mitigation": "v0.1 只做 PC 文件、屏幕关键状态和网页快照。"
}
```

#### automation_opportunity

```json
{
  "title": "每日整理下载目录",
  "pattern": "用户连续 5 天将下载文件手动移动到项目目录。",
  "expected_steps": [
    "扫描下载目录",
    "按文件内容匹配项目",
    "生成移动建议",
    "用户确认后执行"
  ],
  "risk_level": "low",
  "requires_authorization": true
}
```

---

## 10. API 设计

### 10.1 API 风格

v0.1 使用本地 REST API：

```text
http://127.0.0.1:8765/api/v1
```

原则：

- 默认只监听 localhost；
- 局域网访问必须显式开启；
- 所有修改类 API 记录 Audit；
- 高风险 API 必须携带 authorization_id；
- API 返回对象必须包含 ID 和 created_at / updated_at。

---

### 10.2 Source API

#### 创建数据源

```http
POST /api/v1/sources
```

请求：

```json
{
  "source_type": "filesystem",
  "name": "Ego 项目资料",
  "root_uri": "/Users/user/Documents/Ego",
  "privacy_level": "private",
  "scan_policy": {
    "recursive": true,
    "include_extensions": [".md", ".docx", ".pdf", ".pptx", ".xlsx", ".txt"],
    "exclude_patterns": [".git", "node_modules", "*.tmp"]
  },
  "retention_policy": {
    "mode": "keep",
    "max_versions": 20
  }
}
```

响应：

```json
{
  "source_id": "src_20260528_01J0K...",
  "status": "enabled"
}
```

---

### 10.3 Vault API

#### 手动入库

```http
POST /api/v1/vault/ingest
```

请求：

```json
{
  "source_id": "src_20260528_01J0K...",
  "uri": "/Users/user/Documents/Ego/plan.md",
  "ingest_mode": "copy"
}
```

响应：

```json
{
  "raw_object_id": "obj_20260528_01J0K...",
  "version_id": "ver_20260528_01J0K...",
  "evidence_id": "ev_20260528_01J0K...",
  "content_hash": "sha256:..."
}
```

#### 查询证据

```http
GET /api/v1/vault/evidence/{evidence_id}
```

响应：

```json
{
  "evidence_id": "ev_20260528_01J0K...",
  "evidence_type": "document",
  "raw_object_id": "obj_...",
  "version_id": "ver_...",
  "evidence_uri": "vault://objects/documents/...",
  "selector": {},
  "privacy_level": "private",
  "created_at": "2026-05-28T10:00:00+08:00"
}
```

---

### 10.4 Enhancement API

#### 创建增强任务

```http
POST /api/v1/twin/enhance
```

请求：

```json
{
  "evidence_ids": ["ev_20260528_01J0K..."],
  "enhancement_type": "summary",
  "strategy": "auto",
  "privacy_level": "private"
}
```

响应：

```json
{
  "job_id": "job_20260528_01J0K...",
  "status": "pending"
}
```

#### 查询增强结果

```http
GET /api/v1/twin/enhancements?evidence_id=ev_...
```

---

### 10.5 Work Graph API

```http
POST /api/v1/projects/discover
GET  /api/v1/projects
GET  /api/v1/projects/{project_id}
POST /api/v1/tasks/{task_id}/feedback
POST /api/v1/questions/{question_id}/feedback
POST /api/v1/risks/{risk_id}/feedback
```

用户反馈枚举：

```text
confirm | reject | edit | later | convert_to_task | authorize_action
```

---

### 10.6 Brief API

#### 生成 Daily Brief

```http
POST /api/v1/briefs/generate
```

请求：

```json
{
  "report_type": "daily",
  "date": "2026-05-28",
  "project_ids": [],
  "force_regenerate": false
}
```

响应：

```json
{
  "job_id": "job_20260528_01J0K..."
}
```

#### 获取最新 Daily Brief

```http
GET /api/v1/briefs/daily/latest
```

---

### 10.7 Model Router API

```http
POST /api/v1/model-router/run
```

请求：

```json
{
  "purpose": "generate_summary",
  "privacy_level": "private",
  "input_refs": [
    {"type": "evidence", "id": "ev_20260528_01J0K..."}
  ],
  "preferred_runtime": "auto",
  "allow_external": false
}
```

响应：

```json
{
  "invocation_id": "mi_20260528_01J0K...",
  "model_id": "local_qwen_7b_int4",
  "status": "succeeded",
  "output_ref_uri": "vault://model_outputs/mi_...json"
}
```

---

### 10.8 Authorization / Action API

#### 创建动作建议

```http
POST /api/v1/actions/propose
```

#### 用户授权

```http
POST /api/v1/actions/{action_id}/authorize
```

#### 执行动作，v0.1 可先只生成脚本或计划

```http
POST /api/v1/actions/{action_id}/execute
```

原则：

- 删除、移动、发送、上传、提交类动作必须先授权；
- 每个 action_step 必须有执行前后证据；
- v0.1 可将实际执行限制为“生成脚本 + 用户手动运行”。

---

## 11. Night Shift 任务系统

### 11.1 任务生命周期

```text
pending → running → succeeded
                  ↘ failed → pending/retry
                  ↘ blocked
pending → cancelled
```

### 11.2 任务优先级

| 优先级 | 说明 | 示例 |
|---|---|---|
| 0 | 立即任务 | 用户手动生成 Brief |
| 1 | 高优先级后台 | 新文件入库、OCR |
| 2 | 普通后台 | 摘要、标签、项目归类 |
| 3 | 低优先级 | 周报、重复文件检测 |
| 4 | 夜间任务 | 批量重算、模型评测、全量重建 |

### 11.3 任务输入输出

所有 job 的输入输出都用引用，不直接塞大文本。

```json
{
  "job_type": "generate_summary",
  "input_refs": [
    {"type": "evidence", "id": "ev_..."}
  ],
  "output_target": {
    "type": "enhancement",
    "enhancement_type": "summary"
  },
  "policy": {
    "allow_external": false,
    "max_latency_ms": 600000
  }
}
```

### 11.4 失败处理

| 失败类型 | 处理 |
|---|---|
| 文件不存在 | 标记 object missing，写 audit |
| 文档解析失败 | 保存错误，等待人工/新解析器重试 |
| OCR 失败 | 降级为截图 Evidence |
| 本地模型失败 | 可按隐私策略切换外部或等待重试 |
| 外部调用被拒绝 | 标记 policy_blocked |
| 结果无法解析 | 保存原始输出，生成 error enhancement |

---

## 12. Model Router 策略

### 12.1 输入参数

模型选择至少考虑：

| 参数 | 说明 |
|---|---|
| purpose | 任务目的 |
| privacy_level | 隐私等级 |
| input_size | 输入长度 |
| required_quality | 质量要求 |
| latency_budget | 延迟预算 |
| cost_budget | 成本预算 |
| local_model_available | 本地模型是否可用 |
| external_allowed | 是否允许外部调用 |
| can_retry | 是否可重试 |

### 12.2 默认策略

```text
critical  → 禁止模型读取，除非用户逐次授权
sensitive → 仅本地模型或规则
private   → 默认本地；外部需明确策略允许
public    → 可外部处理
```

### 12.3 路由伪代码

```python
def select_model(task):
    if task.privacy_level == "critical":
        return deny("critical data requires explicit authorization")

    if task.privacy_level == "sensitive":
        return best_local_model(task)

    if task.purpose in {"ocr", "file_hash", "metadata_extract"}:
        return rule_or_local_tool(task)

    if task.input_size < SMALL_CONTEXT and local_model_sufficient(task):
        return best_local_model(task)

    if task.allow_external and task.privacy_level in {"public", "private"}:
        return external_or_local_by_quality_cost(task)

    return local_batch_queue(task)
```

### 12.4 模型可替换设计

所有模型通过 Adapter 接入。

```python
class ModelAdapter:
    def generate(self, request: ModelRequest) -> ModelResponse: ...
    def embed(self, request: EmbedRequest) -> EmbedResponse: ...
    def health(self) -> ModelHealth: ...
```

Adapter 类型：

- OllamaAdapter；
- LlamaCppAdapter；
- VllmAdapter；
- RknnAdapter；
- ExternalOpenAICompatibleAdapter；
- RuleBasedAdapter。

---

## 13. Compute Fabric 设计

### 13.1 Compute Node 类型

| 类型 | 示例 | 作用 |
|---|---|---|
| local_pc | 当前 PC | 文档解析、本地小模型 |
| ego_node | RK3588 / Ego Node S | 常驻控制、轻量视觉 |
| lan_server | 局域网 GPU 服务器 | 批量增强、高质量本地模型 |
| external_api | 外部模型 API | 高难任务增强 |
| future_dock | 专用算力舱 | 未来硬件扩展 |

### 13.2 节点能力描述

```json
{
  "compute_node_id": "cmp_lan_a800_001",
  "node_type": "lan_server",
  "capabilities": {
    "cpu": "x86_64",
    "gpu": "NVIDIA A800 x3",
    "memory_gb": 256,
    "runtimes": ["vllm", "ollama", "python_sandbox"],
    "models": ["qwen3-32b", "deepseek-r1-distill-32b"]
  },
  "trust_level": "trusted_lan",
  "default_privacy_allowed": ["public", "private"],
  "energy_meter_available": false
}
```

### 13.3 v0.1 不做复杂分布式

v0.1 只需要：

1. 登记本地 PC；
2. 登记一个可选局域网服务器；
3. 登记一个可选外部模型 provider；
4. 能够按任务选择运行位置；
5. 记录调用时间、耗时、成本、隐私等级。

不要在 v0.1 做公网 P2P、节点结算、区块链、可信执行环境。

---

## 14. 安全与权限设计

### 14.1 权限控制对象

| 对象 | 权限 |
|---|---|
| Source | enable / disable / scan / delete |
| Evidence | read / export / delete / external_process |
| Enhancement | read / verify / reject / recompute |
| Model Invocation | allow_local / allow_external |
| Action | propose / authorize / execute / cancel |
| Report | generate / view / export |
| Audit | append / view，不允许 update/delete |

### 14.2 高风险动作清单

以下动作必须逐次授权：

- 删除文件；
- 覆盖文件；
- 批量移动文件；
- 发送邮件或消息；
- 提交表单；
- 上传文件；
- 修改代码仓库主分支；
- 修改合同、报价、发票；
- 支付或财务操作；
- 修改系统设置；
- 启动外部共享。

### 14.3 审计事件类型

```text
source.created
source.enabled
source.disabled
object.ingested
version.created
evidence.created
enhancement.created
enhancement.verified
enhancement.rejected
model.invoked
model.blocked_by_policy
brief.generated
action.proposed
action.authorized
action.executed
action.failed
policy.updated
data.exported
data.deleted
```

### 14.4 外部模型调用规则

外部调用前必须执行：

1. 检查 Evidence 隐私等级；
2. 检查 Source 策略；
3. 检查用户全局策略；
4. 生成最小上下文；
5. 必要时脱敏；
6. 写入 model_invocations；
7. 写入 audit_logs。

---

## 15. Brief Engine 设计

### 15.1 Daily Brief 生成输入

| 输入 | 来源 |
|---|---|
| 昨日新增 Evidence | evidence / object_versions |
| 昨日新增 Enhancement | enhancements |
| 项目变化 | projects / project_links |
| 新增任务 | tasks |
| 新增问题 | questions |
| 风险 | risks |
| 自动化机会 | automations |
| 用户反馈 | report_items / feedback |

### 15.2 Daily Brief 结构

```text
1. 昨日主要项目
2. 新增重要资料
3. 文件归类建议
4. 未完成事项
5. 风险与冲突
6. 值得追问的问题
7. Ego 可自动完成的工作
8. 需要你授权的动作
9. 证据链接
```

### 15.3 Brief Item 类型

| 类型 | 说明 |
|---|---|
| project_update | 项目变化 |
| new_evidence | 新增资料 |
| task | 待办 |
| question | 问题 |
| risk | 风险 |
| automation | 自动化机会 |
| decision | 需要决策 |
| data_health | 数据健康 |
| system | 系统状态 |

### 15.4 Brief 质量约束

- 不超过用户可读负担；
- 每条重要结论必须有证据；
- 不确定内容必须标注 `inferred`；
- 相同内容不重复提醒；
- 用户驳回过的模式降低权重；
- 用户确认过的模式提高权重。

---

## 16. Operator Bridge 预留接口

v0.1 先不做完整 Ghost Control，但必须让 Data Core 能向 Operator 提供上下文。

### 16.1 Action Plan 数据结构

```json
{
  "action_id": "act_20260528_01J0K...",
  "title": "整理 Ego 项目目录",
  "risk_level": "medium",
  "requires_authorization": true,
  "goal": "将散落的 Ego 项目文档按产品、技术、融资三类整理到项目目录。",
  "input_refs": [
    {"type": "project", "id": "proj_ego_data_core"},
    {"type": "evidence", "id": "ev_..."}
  ],
  "steps": [
    {"type": "inspect_folder", "target": "/Documents/Ego"},
    {"type": "propose_moves", "mode": "dry_run"},
    {"type": "user_confirm"},
    {"type": "execute_moves"},
    {"type": "verify_folder"}
  ]
}
```

### 16.2 v0.1 执行模式

v0.1 只允许三种执行：

| 模式 | 说明 |
|---|---|
| dry_run | 只生成计划，不改数据 |
| script_generation | 生成脚本，用户手动执行 |
| supervised_execute | 用户授权后执行低风险动作 |

不允许默认自动删除、发送、上传、支付。

---

## 17. 搜索与向量设计

### 17.1 搜索分三类

| 类型 | 说明 |
|---|---|
| Metadata Search | 文件名、时间、路径、类型、项目 |
| Full-text Search | evidence_text_chunks 的全文搜索 |
| Semantic Search | 向量库检索 |

### 17.2 向量不是记忆本体

向量只用于检索。

- 向量可以删除重建；
- 向量必须记录来源 Evidence；
- 向量模型升级后可重建；
- 向量库损坏不影响原始数据；
- 不允许只保存向量而删除 Evidence。

### 17.3 embeddings 表用途

SQLite 主库只保存：

- subject_type；
- subject_id；
- model_id；
- vector_store；
- vector_ref；
- dimension；
- created_at。

实际向量保存在 LanceDB / Qdrant。

---

## 18. 开发目录结构

建议仓库结构：

```text
ego-data-core/
  apps/
    api/
      main.py
      routes/
      dependencies.py
    web/
      src/
  core/
    kernel/
      policy_engine.py
      identity.py
      config.py
    vault/
      ingest.py
      evidence.py
      versions.py
      text_chunks.py
    twin/
      enhance.py
      schemas.py
      trace.py
    graph/
      projects.py
      tasks.py
      risks.py
      questions.py
      automations.py
    brief/
      daily.py
      templates.py
      evidence_links.py
    scheduler/
      jobs.py
      runner.py
      retry.py
    model_router/
      router.py
      adapters/
        ollama.py
        llama_cpp.py
        vllm.py
        external_openai_compatible.py
        rules.py
    compute/
      nodes.py
      health.py
      dispatch.py
    safety/
      privacy.py
      authorization.py
      audit.py
    operator_bridge/
      actions.py
      action_steps.py
      dry_run.py
  connectors/
    filesystem/
      watcher.py
      scanner.py
    screen/
      capture.py
      active_window.py
      ocr.py
    browser/
      snapshot.py
  storage/
    migrations/
      001_init.sql
    repository/
      base.py
      sources.py
      evidence.py
      enhancements.py
      reports.py
  prompts/
    summary_v1.md
    project_classify_v1.md
    task_extract_v1.md
    risk_detect_v1.md
    daily_brief_v1.md
  tests/
    unit/
    integration/
    fixtures/
  docs/
```

---

## 19. Pydantic 模型草案

### 19.1 Evidence

```python
class Evidence(BaseModel):
    evidence_id: str
    raw_object_id: str
    version_id: str | None = None
    evidence_type: Literal[
        "document", "screenshot", "text_span", "image_region",
        "web_snapshot", "event", "operator_log"
    ]
    evidence_uri: str | None = None
    evidence_selector: dict = Field(default_factory=dict)
    content_hash: str | None = None
    privacy_level: Literal["public", "private", "sensitive", "critical"]
    retention_policy: Literal["keep", "rolling", "manual_review"] = "keep"
    captured_at: datetime
    created_at: datetime
```

### 19.2 Enhancement

```python
class Enhancement(BaseModel):
    enhancement_id: str
    enhancement_type: str
    status: Literal["draft", "verified", "rejected", "superseded", "error"] = "draft"
    content: dict
    confidence: float | None = None
    model_id: str | None = None
    model_runtime: str | None = None
    prompt_hash: str | None = None
    evidence_ids: list[str]
    generated_at: datetime
```

### 19.3 Report Item

```python
class ReportItem(BaseModel):
    report_item_id: str
    report_id: str
    item_type: Literal[
        "project_update", "new_evidence", "task", "question", "risk",
        "automation", "decision", "data_health", "system"
    ]
    title: str
    body: str
    severity: Literal["info", "low", "medium", "high", "critical"] = "info"
    confidence: float | None = None
    evidence_ids: list[str]
    user_feedback: str | None = None
```

---

## 20. v0.1 里程碑拆解

### Milestone 1：DB + Source + Vault

验收：

- SQLite schema 可初始化；
- 能创建 Source；
- 能扫描目录；
- 能生成 Raw Object / Version / Evidence；
- 能查看 Evidence 列表。

### Milestone 2：Document Parser + Text Chunks

验收：

- 支持 md/txt/pdf/docx 基础解析；
- 能写入 evidence_text_chunks；
- 能全文检索；
- 能查看原文证据。

### Milestone 3：Enhancement Pipeline

验收：

- 能对 Evidence 生成 summary/tag/project_link；
- Enhancement 与 Evidence 可追溯；
- 模型调用进入 model_invocations；
- 外部调用受隐私策略限制。

### Milestone 4：Work Graph

验收：

- 能生成 Project；
- 能提取 Task / Question / Risk；
- 能关联 Evidence；
- 用户能确认/驳回。

### Milestone 5：Daily Brief

验收：

- 能按日期生成 Daily Brief；
- 每个 Report Item 有证据；
- 用户能反馈；
- Brief 能导出 Markdown。

### Milestone 6：Operator Bridge + Demo

验收：

- 能生成 Action Plan；
- 能执行 dry_run；
- 能生成脚本；
- 能记录 authorization 和 audit；
- 形成 5 分钟投资人 Demo。

---

## 21. 给 Codex 的首轮开发任务

### Task 1：初始化项目骨架

```text
创建 ego-data-core 仓库，使用 Python 3.11 + FastAPI + SQLite。
实现 /health、/api/v1/sources、/api/v1/vault/ingest 三个最小接口。
加入 storage/migrations/001_init.sql，并在启动时可初始化数据库。
```

### Task 2：实现 ID 生成器

```text
实现 core/kernel/id_generator.py。
支持 usr/dev/src/obj/ver/ev/chk/enh/proj/task/q/risk/auto/brief/job/mi/act/aud 等前缀。
ID 使用 prefix + YYYYMMDD + ULID 或安全随机字符串。
```

### Task 3：实现文件夹扫描

```text
实现 connectors/filesystem/scanner.py。
输入 source_id 和 root_uri，扫描文件，计算 sha256，创建 raw_objects、object_versions、evidence。
不要修改用户原始目录。
```

### Task 4：实现文档文本解析

```text
实现 connectors/documents/parser.py。
先支持 .txt、.md、.pdf、.docx。
解析结果写入 vault/extracted_text，并建立 evidence_text_chunks。
```

### Task 5：实现 Enhancement Pipeline 最小版

```text
实现 twin/enhance.py。
先支持 summary 和 tag 两种 enhancement_type。
模型适配先做 RuleBasedAdapter + OllamaAdapter 接口。
Enhancement 必须写入 enhancement_evidence_links。
```

### Task 6：实现 Daily Brief 最小版

```text
实现 brief/daily.py。
输入日期，读取当天新增 evidence、enhancement、task、risk、question。
生成 report 和 report_items。
输出 Markdown 格式，并提供 GET /briefs/daily/latest。
```

---

## 22. 当前定稿结论

Ego Data Core v0.1 的技术架构必须牢牢围绕一个闭环：

```text
Evidence → Enhancement → Work Graph → Brief → Authorization → Action → Audit
```

其中最重要的是前两层：

> **Evidence 是不可替代的原始数据资产；Enhancement 是可重算的智能解释层。**

只要这条架构成立，Ego 就不会退化成普通知识库、API 网关或聊天助手。后续无论模型如何变化、芯片如何变化、算力从哪里来，Ego 都能保持自己的核心：

> **本地保存用户数据主权，持续增强用户数据资产，并逐步把数据转化为可执行的主动行动。**
