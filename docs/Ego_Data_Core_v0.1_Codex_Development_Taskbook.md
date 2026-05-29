# Ego Data Core v0.1 Codex 开发任务书

**版本**：v0.1 内部执行稿  
**日期**：2026-05-28  
**项目代号**：Ego / ShadowNode  
**对应文档**：

- 《Ego Data Core v0.1 产品定义》
- 《Ego Data Core v0.1 技术架构与数据库 Schema》
- `ego_data_core_v0_1_schema.sqlite.sql`
- `ego_data_core_v0_1_openapi.yaml`

**文档目的**：把 Ego Data Core v0.1 拆成可以直接交给 Codex 执行的 Issue、模块、接口、目录、测试用例和验收标准。

---

## 0. 当前开发总目标

90 天内完成一个可演示、可迭代的 Ego Data Core v0.1：

> 用户授权一个本地工作目录，Ego 只读扫描文件，保存原始证据，生成增强数据，发现项目、任务、问题和风险，并每天输出一份有证据引用的 Ego Daily Brief。

v0.1 的核心闭环：

```text
Source → Raw Object → Object Version → Evidence → Enhancement → Work Graph → Daily Brief → Feedback → Audit
```

v0.1 的投资人/内部演示闭环：

```text
指定工作目录
  ↓
一键扫描入库
  ↓
生成摘要、标签、待办、风险、项目候选
  ↓
生成 Ego Daily Brief
  ↓
用户确认/驳回/授权 dry-run 动作
  ↓
显示所有结论的证据来源和审计记录
```

---

## 1. 不可违反的工程原则

### 1.1 Evidence-first

原始证据是最高事实层。文件原件、截图、网页快照、操作日志等不能被模型摘要替代。

所有 Enhancement、Task、Question、Risk、Brief Item 都必须尽量关联 Evidence。没有证据的内容只能标记为 system/data_health/insufficient_evidence，不能伪装成事实。

### 1.2 Non-destructive

v0.1 严禁修改用户原始目录。

禁止：

- 自动移动用户文件；
- 自动删除用户文件；
- 自动重命名用户文件；
- 自动上传用户文件；
- 自动发送用户文件；
- 用模型输出覆盖原始数据。

v0.1 的动作执行最多做到 `dry_run`、脚本生成和授权记录。

### 1.3 Local-first

核心数据库、Vault、Brief、Audit 默认保存在本地。外部模型、云端算力、局域网服务器都是可选增强，不是 v0.1 必要依赖。

### 1.4 Model-agnostic

系统不得绑定某一个模型。第一版必须在没有 Ollama、没有云 API 的情况下，依靠 RuleBasedAdapter 跑通 Demo。

### 1.5 Async-first

Ego 不是即时聊天产品。v0.1 优先实现后台任务队列 Night Shift：扫描、解析、增强、发现、Brief 生成都以 job 形式运行。

### 1.6 Audit everything

采集、扫描、解析、增强、模型调用、策略阻断、用户反馈、授权、错误都必须写入 Audit Log。

---

## 2. v0.1 最小技术栈

| 层级 | 建议技术 |
|---|---|
| 语言 | Python 3.11 |
| API | FastAPI |
| 数据库 | SQLite，后续可迁移 PostgreSQL |
| 本地文件存储 | Ego Vault 本地目录 |
| 文档解析 | txt/md 原生；pdf/docx 可选依赖 |
| 任务队列 | SQLite jobs 表 + 单进程 worker |
| 模型适配 | RuleBasedAdapter P0；OllamaAdapter P1 |
| UI | FastAPI 静态页面 + 原生 JS，P1 |
| 测试 | pytest |
| CLI | Typer 或 argparse |
| 打包 | pyproject.toml，优先 uv/pip 均可 |

---

## 3. 推荐仓库目录

```text
ego-data-core/
├── README.md
├── pyproject.toml
├── .env.example
├── .gitignore
├── docs/
│   ├── product_definition.md
│   ├── technical_architecture.md
│   ├── api_contract.md
│   ├── demo_script.md
│   └── security_and_privacy.md
├── scripts/
│   ├── init_db.py
│   ├── run_worker.py
│   ├── run_demo.sh
│   └── export_brief.py
├── demo/
│   └── sample_workspace/
├── storage/
│   └── migrations/
│       └── 001_init.sql
├── src/
│   └── ego_data_core/
│       ├── __init__.py
│       ├── main.py
│       ├── cli.py
│       ├── api/
│       │   ├── app.py
│       │   ├── deps.py
│       │   └── routes/
│       │       ├── health.py
│       │       ├── sources.py
│       │       ├── vault.py
│       │       ├── twin.py
│       │       ├── projects.py
│       │       ├── briefs.py
│       │       ├── actions.py
│       │       ├── audit.py
│       │       └── search.py
│       ├── kernel/
│       │   ├── config.py
│       │   ├── id_generator.py
│       │   ├── errors.py
│       │   ├── logging.py
│       │   └── time.py
│       ├── storage/
│       │   ├── db.py
│       │   ├── migrations.py
│       │   └── repositories/
│       ├── safety/
│       │   └── policy.py
│       ├── audit/
│       │   └── service.py
│       ├── connectors/
│       │   ├── source_service.py
│       │   ├── filesystem/
│       │   │   └── scanner.py
│       │   ├── documents/
│       │   │   └── parser.py
│       │   └── screen/
│       │       └── capture.py
│       ├── vault/
│       │   ├── storage.py
│       │   ├── ingest.py
│       │   └── search.py
│       ├── twin/
│       │   ├── enhance.py
│       │   └── screenshot_ocr.py
│       ├── workgraph/
│       │   ├── project_discovery.py
│       │   ├── extractors.py
│       │   └── automation_opportunities.py
│       ├── brief/
│       │   ├── daily.py
│       │   ├── export_markdown.py
│       │   └── data_health.py
│       ├── nightshift/
│       │   ├── queue.py
│       │   └── worker.py
│       ├── model_router/
│       │   ├── base.py
│       │   ├── service.py
│       │   ├── rule_based.py
│       │   └── ollama_adapter.py
│       ├── compute_fabric/
│       │   └── nodes.py
│       ├── operator/
│       │   └── bridge.py
│       └── ui/
│           └── static/
└── tests/
    ├── conftest.py
    ├── api/
    ├── audit/
    ├── brief/
    ├── connectors/
    ├── kernel/
    ├── model_router/
    ├── nightshift/
    ├── operator/
    ├── safety/
    ├── storage/
    ├── twin/
    ├── vault/
    └── workgraph/
```

---

## 4. Codex 开发规则

### 4.1 每次只做一个 Issue

每个 Issue 应形成一个独立 PR 或 commit。不要一次性让 Codex 写完整系统。

标准执行格式：

```text
任务：EDC-xxx
上下文：粘贴对应 Issue 卡片 + 相关 schema/API 片段
要求：只实现本 Issue，不改动无关模块
测试：必须新增或更新对应 pytest
验收：逐条检查验收标准
```

### 4.2 每个 Issue 的交付物

每个 Issue 至少包含：

1. 代码实现；
2. 单元测试或 API 测试；
3. README 或 docstring 中的使用说明；
4. 错误处理；
5. 审计记录，若涉及数据变更；
6. 不破坏已有测试。

### 4.3 Codex 禁止事项

Codex 不得：

- 硬编码用户真实路径；
- 默认扫描用户全盘；
- 默认访问网络；
- 默认调用云模型；
- 在测试中读写真用户目录；
- 让后台任务静默失败；
- 直接删除、移动、重命名用户文件；
- 把模型输出当作原始事实写入 Evidence；
- 绕过 Safety Kernel 调用外部模型；
- 绕过 Audit 直接执行动作。

---

## 5. 里程碑计划

### M0：Project Foundation

目标：可启动、可测试、可配置。

包含：EDC-000、EDC-003、EDC-028、EDC-029。

验收：

- API 可启动；
- `/api/v1/health` 正常；
- pytest 可运行；
- 临时数据目录隔离；
- 错误响应格式稳定。

### M1：DB + Source + Vault

目标：本地数据库、数据源、文件扫描和 Evidence 入库跑通。

包含：EDC-001、EDC-002、EDC-004、EDC-005、EDC-006、EDC-007。

验收：

- SQLite schema 初始化成功；
- Source 可创建；
- 指定目录只读扫描；
- Raw Object / Version / Evidence 可生成；
- Audit 可查询。

### M2：Document Parser + Search

目标：文档文本可抽取、可分块、可检索。

包含：EDC-008、EDC-009。

验收：

- txt/md/pdf/docx 基础解析；
- 写入 extracted_text 与 chunks；
- 可搜索关键字；
- 解析失败可审计、可重试。

### M3：Enhancement Pipeline + Safety

目标：后台增强流水线跑通，模型可替换，外部调用受控。

包含：EDC-010、EDC-011、EDC-012、EDC-013、EDC-020。

验收：

- Job Queue 可执行任务；
- RuleBasedAdapter 可生成 summary/tag；
- Ollama 可选，不影响主流程；
- Enhancement 可追溯 Evidence；
- sensitive/critical 策略生效。

### M4：Work Graph

目标：生成项目、任务、问题、风险、自动化机会。

包含：EDC-014、EDC-015、EDC-016。

验收：

- 项目候选可生成；
- Task/Question/Risk 可提取；
- Automation Opportunity 只建议不执行；
- 用户反馈可记录。

### M5：Daily Brief

目标：每天输出一份有证据支撑的 Ego Daily Brief。

包含：EDC-017、EDC-018、EDC-019、EDC-025、EDC-027。

验收：

- Daily Brief 可生成；
- Markdown 可导出；
- 每个关键条目有 Evidence；
- UI/CLI 至少一个入口可完整展示；
- Data Health 能提示系统覆盖度和失败项。

### M6：Operator Bridge + Demo

目标：完成 5 分钟投资人 Demo：数据入库、增强、简报、动作 dry-run、审计。

包含：EDC-021、EDC-022、EDC-023、EDC-024、EDC-026、EDC-030。

验收：

- Action Plan dry-run 可演示；
- 手动截图可入库；
- OCR 适配接口存在；
- Compute Node 可注册；
- Demo 脚本可一键跑通；
- OpenAPI 契约基本一致。

---

## 6. Issue 总览

| ID | 优先级 | 里程碑 | 模块 | 标题 |
|---|---:|---|---|---|
| EDC-000 | P0 | M0 Project Foundation | repo | 建立仓库骨架与工程约束 |
| EDC-001 | P0 | M1 DB + Vault | storage | SQLite 初始化与迁移管理 |
| EDC-002 | P0 | M1 DB + Vault | kernel | 统一 ID 生成器 |
| EDC-003 | P0 | M0 Project Foundation | kernel | 配置系统与本地目录规范 |
| EDC-004 | P0 | M1 DB + Vault | audit | Audit Log 最小实现 |
| EDC-005 | P0 | M1 DB + Vault | api/connectors | Source 管理 API |
| EDC-006 | P0 | M1 DB + Vault | connectors/filesystem | 文件系统扫描器 v0 |
| EDC-007 | P0 | M1 DB + Vault | vault | Vault 文件存储与 URI 规范 |
| EDC-008 | P0 | M2 Document Parser | connectors/documents | 文档解析器 v0：txt/md/pdf/docx |
| EDC-009 | P1 | M2 Document Parser | vault/search | 全文检索最小实现 |
| EDC-010 | P0 | M3 Enhancement Pipeline | nightshift | Night Shift Job Queue v0 |
| EDC-011 | P0 | M3 Enhancement Pipeline | model_router | Model Router 接口与 RuleBasedAdapter |
| EDC-012 | P1 | M3 Enhancement Pipeline | model_router | OllamaAdapter 可选本地模型适配 |
| EDC-013 | P0 | M3 Enhancement Pipeline | twin | Enhancement Pipeline：summary/tag |
| EDC-014 | P1 | M4 Work Graph | workgraph | Project Discovery v0 |
| EDC-015 | P1 | M4 Work Graph | workgraph | Task / Question / Risk 提取 v0 |
| EDC-016 | P2 | M4 Work Graph | workgraph/operator | Automation Opportunity 发现 v0 |
| EDC-017 | P0 | M5 Daily Brief | brief | Daily Brief 生成器 v0 |
| EDC-018 | P0 | M5 Daily Brief | brief/vault | Markdown 导出器与证据引用格式 |
| EDC-019 | P1 | M5 Daily Brief | ui | 本地 Web UI 最小版 |
| EDC-020 | P0 | M3 Enhancement Pipeline | safety | Safety Kernel：隐私等级与外部调用策略 |
| EDC-021 | P1 | M6 Operator Bridge + Demo | operator | Operator Bridge：Action Plan Dry-run |
| EDC-022 | P1 | M6 Operator Bridge + Demo | connectors/screen | 屏幕采集 Connector v0：手动截图入库 |
| EDC-023 | P1 | M6 Operator Bridge + Demo | twin/screen | Screenshot OCR Enhancement v0 |
| EDC-024 | P2 | M6 Operator Bridge + Demo | compute_fabric | Compute Fabric 节点注册 v0 |
| EDC-025 | P1 | M5 Daily Brief | cli | CLI 工具：扫描、增强、生成 Brief |
| EDC-026 | P0 | M6 Operator Bridge + Demo | demo | Demo Seed 数据与一键演示脚本 |
| EDC-027 | P2 | M5 Daily Brief | brief/data_health | 数据健康检查 Data Health |
| EDC-028 | P0 | M0 Project Foundation | kernel/logging | 错误处理与日志规范 |
| EDC-029 | P0 | M0 Project Foundation | tests | 测试基座与临时工作区 Fixture |
| EDC-030 | P1 | M6 Operator Bridge + Demo | api | OpenAPI 同步与契约测试 |

---

## 7. 详细 Issue 卡片


### EDC-000｜建立仓库骨架与工程约束

- **里程碑**：M0 Project Foundation
- **优先级**：P0
- **模块**：repo
- **依赖**：无
- **任务说明**：创建 ego-data-core Python/FastAPI 项目骨架，固定目录结构、依赖管理、基础配置和开发命令。
- **输入**：Ego_Data_Core_v0.1_Technical_Architecture_and_Schema.md; ego_data_core_v0_1_schema.sqlite.sql; ego_data_core_v0_1_openapi.yaml
- **输出**：pyproject.toml; src/ego_data_core/; tests/; scripts/; .env.example; README.md

**验收标准**
- python -m ego_data_core.main 或 uvicorn ego_data_core.api.app:app 可启动本地 API
- GET /api/v1/health 返回 ok、版本号、数据库状态
- README 中包含本地启动、初始化数据库、运行测试的命令
- 不得创建任何会修改用户原始文件的逻辑

**测试**
- `pytest tests/test_health.py`

**给 Codex 的任务提示词**

```text
请创建 ego-data-core 的 Python 3.11 + FastAPI 项目骨架。使用 src layout，保留清晰模块边界：api、kernel、storage、connectors、vault、twin、workgraph、brief、nightshift、model_router、compute_fabric、operator、safety、audit。先实现 /api/v1/health，加入 README、.env.example 和基础 pytest。
```

### EDC-001｜SQLite 初始化与迁移管理

- **里程碑**：M1 DB + Vault
- **优先级**：P0
- **模块**：storage
- **依赖**：EDC-000
- **任务说明**：接入现有 SQLite Schema，建立本地数据库初始化、迁移执行、连接管理和事务封装。
- **输入**：ego_data_core_v0_1_schema.sqlite.sql
- **输出**：src/ego_data_core/storage/db.py; src/ego_data_core/storage/migrations/001_init.sql; scripts/init_db.py

**验收标准**
- 首次启动可自动创建数据库
- PRAGMA foreign_keys = ON
- schema 全部表可创建成功
- 重复执行迁移不破坏已有数据

**测试**
- `pytest tests/storage/test_db_init.py`

**给 Codex 的任务提示词**

```text
请实现 SQLite 初始化与迁移系统。把现有 schema 放入 storage/migrations/001_init.sql；提供 get_connection、transaction、run_migrations。所有连接开启 foreign_keys。写 pytest 验证 schema 可创建、关键表存在、重复迁移安全。
```

### EDC-002｜统一 ID 生成器

- **里程碑**：M1 DB + Vault
- **优先级**：P0
- **模块**：kernel
- **依赖**：EDC-000
- **任务说明**：实现带前缀、日期和随机/ULID 后缀的统一对象 ID，覆盖 User、Device、Source、Object、Evidence、Job 等核心实体。
- **输入**：无
- **输出**：src/ego_data_core/kernel/id_generator.py

**验收标准**
- 支持 usr/dev/src/obj/ver/ev/chk/enh/proj/task/q/risk/auto/brief/job/mi/act/aud/report/item 等前缀
- ID 可排序或至少可按日期识别
- 10 万次生成无碰撞
- 非法前缀会抛出明确异常

**测试**
- `pytest tests/kernel/test_id_generator.py`

**给 Codex 的任务提示词**

```text
请实现统一 ID 生成器。格式建议 prefix_YYYYMMDD_<ulid_or_secure_random>。要求可测试、无全局状态污染、非法前缀报错。为所有 v0.1 实体预置允许前缀，并写碰撞测试。
```

### EDC-003｜配置系统与本地目录规范

- **里程碑**：M0 Project Foundation
- **优先级**：P0
- **模块**：kernel
- **依赖**：EDC-000
- **任务说明**：建立 Ego 本地工作目录、Vault 目录、日志目录、模型配置、隐私策略配置。
- **输入**：无
- **输出**：src/ego_data_core/kernel/config.py; .env.example

**验收标准**
- 默认数据目录为用户主目录下 .ego_data_core 或环境变量 EGO_DATA_HOME
- Vault、extracted_text、model_outputs、briefs、logs、tmp 目录自动创建
- 配置项不包含硬编码绝对路径
- 配置支持 dev/test/prod 三类 profile

**测试**
- `pytest tests/kernel/test_config.py`

**给 Codex 的任务提示词**

```text
请实现配置系统。使用 pydantic-settings 或等价轻量方案。默认 EGO_DATA_HOME=~/.ego_data_core，可用环境变量覆盖。启动时创建 vault 子目录：objects、versions、evidence、extracted_text、model_outputs、briefs、logs、tmp。
```

### EDC-004｜Audit Log 最小实现

- **里程碑**：M1 DB + Vault
- **优先级**：P0
- **模块**：audit
- **依赖**：EDC-001, EDC-002
- **任务说明**：所有采集、增强、模型调用、策略拦截、用户授权与错误必须写入审计日志。
- **输入**：schema audit 相关表
- **输出**：src/ego_data_core/audit/service.py

**验收标准**
- 提供 append_audit_log(event_type, actor, target, payload) 方法
- 审计记录不可被普通业务代码更新，只允许追加
- GET /api/v1/audit/logs 可分页查询
- 错误也必须可写 audit

**测试**
- `pytest tests/audit/test_audit_service.py`

**给 Codex 的任务提示词**

```text
请实现 AuditService。提供追加审计日志和分页查询。事件类型包括 source_created、object_ingested、evidence_created、job_created、model_invoked、policy_blocked、brief_generated、action_authorized、error。不要实现删除审计日志的业务接口。
```

### EDC-005｜Source 管理 API

- **里程碑**：M1 DB + Vault
- **优先级**：P0
- **模块**：api/connectors
- **依赖**：EDC-001, EDC-004
- **任务说明**：实现数据源创建、列表、启用/停用和隐私等级配置。
- **输入**：OpenAPI /sources
- **输出**：src/ego_data_core/api/routes/sources.py; src/ego_data_core/connectors/source_service.py

**验收标准**
- POST /sources 可创建 filesystem/screen/browser/manual source
- GET /sources 返回 source 列表
- 创建时写 audit
- 默认 privacy_level=private

**测试**
- `pytest tests/api/test_sources.py`

**给 Codex 的任务提示词**

```text
请实现 Source 管理 API。严格按 OpenAPI 草案实现 GET/POST /api/v1/sources，字段包括 source_type、name、root_uri、privacy_level、scan_policy、retention_policy。写入数据库 sources 表，并写 audit。
```

### EDC-006｜文件系统扫描器 v0

- **里程碑**：M1 DB + Vault
- **优先级**：P0
- **模块**：connectors/filesystem
- **依赖**：EDC-005, EDC-002, EDC-003
- **任务说明**：扫描指定目录，计算文件哈希，生成 Raw Object、Object Version 和 Evidence。不得修改用户原目录。
- **输入**：filesystem source
- **输出**：src/ego_data_core/connectors/filesystem/scanner.py

**验收标准**
- 支持递归扫描，可配置 max_depth、include/exclude glob
- 计算 sha256、文件大小、mtime、mime type
- 新文件生成 raw_objects、object_versions、evidence
- 同 hash 文件不重复复制，或能标记重复关系
- 扫描过程只读，不移动、不改名、不删除用户文件

**测试**
- `pytest tests/connectors/test_filesystem_scanner.py`

**给 Codex 的任务提示词**

```text
请实现只读文件系统扫描器。输入 source_id，读取 sources.root_uri 和 scan_policy_json。递归扫描常见文档文件，计算 sha256，复制版本到 Ego Vault 的 versions 目录，写 raw_objects、object_versions、evidence。严禁修改用户原目录。
```

### EDC-007｜Vault 文件存储与 URI 规范

- **里程碑**：M1 DB + Vault
- **优先级**：P0
- **模块**：vault
- **依赖**：EDC-003, EDC-006
- **任务说明**：定义 vault:// URI 映射到本地文件系统，封装对象版本、证据、文本、模型输出的读写路径。
- **输入**：无
- **输出**：src/ego_data_core/vault/storage.py

**验收标准**
- 支持 vault://objects、vault://versions、vault://evidence、vault://extracted_text、vault://model_outputs、vault://briefs
- 所有写入路径防止目录穿越
- 提供 resolve_uri 与 safe_write_json/safe_write_text/safe_copy_file
- 文件名中不直接暴露用户敏感原路径

**测试**
- `pytest tests/vault/test_storage_uri.py`

**给 Codex 的任务提示词**

```text
请实现 VaultStorage。定义 vault:// URI 到 EGO_DATA_HOME/vault 的映射，支持安全复制文件、写 JSON、写文本、读取文本、校验 URI。必须防止 ../ 路径穿越，不能把用户原始绝对路径作为 Vault 文件名。
```

### EDC-008｜文档解析器 v0：txt/md/pdf/docx

- **里程碑**：M2 Document Parser
- **优先级**：P0
- **模块**：connectors/documents
- **依赖**：EDC-006, EDC-007
- **任务说明**：对 Object Version 提取文本，生成 extracted_text_uri 和 evidence_text_chunks。
- **输入**：object_versions
- **输出**：src/ego_data_core/connectors/documents/parser.py

**验收标准**
- 支持 .txt、.md、.pdf、.docx 基础文本提取
- 解析失败不得中断扫描，写 error audit 与 job failure
- 按段落/长度分块写 evidence_text_chunks
- chunk 记录 evidence_id、chunk_index、text、char_start/char_end 或 metadata

**测试**
- `pytest tests/connectors/test_document_parser.py`

**给 Codex 的任务提示词**

```text
请实现文档解析器 v0。先支持 txt/md/pdf/docx。可用 pypdf、python-docx 等轻量库；库不可用时要优雅降级。把抽取文本写到 vault://extracted_text，并按 800-1200 字符分块写 evidence_text_chunks。
```

### EDC-009｜全文检索最小实现

- **里程碑**：M2 Document Parser
- **优先级**：P1
- **模块**：vault/search
- **依赖**：EDC-008
- **任务说明**：基于 SQLite FTS5 或降级 LIKE 实现本地文本搜索，支持按 evidence、source、date 过滤。
- **输入**：evidence_text_chunks
- **输出**：src/ego_data_core/vault/search.py; GET /api/v1/search

**验收标准**
- 能按关键词返回 chunk、evidence_id、raw_object title、score 或匹配信息
- 支持 source_id 和日期过滤
- 返回结果不直接暴露未授权路径
- FTS5 不可用时有降级方案

**测试**
- `pytest tests/vault/test_search.py`

**给 Codex 的任务提示词**

```text
请实现本地全文检索。优先使用 SQLite FTS5 建立 evidence_chunks_fts；若环境不支持 FTS5，降级为 LIKE 搜索。新增 GET /api/v1/search?q=。返回 evidence_id、chunk_id、snippet、title、captured_at。
```

### EDC-010｜Night Shift Job Queue v0

- **里程碑**：M3 Enhancement Pipeline
- **优先级**：P0
- **模块**：nightshift
- **依赖**：EDC-001, EDC-004
- **任务说明**：实现 SQLite 驱动的本地任务队列，支持 pending/running/succeeded/failed/blocked/cancelled 和重试。
- **输入**：jobs 表
- **输出**：src/ego_data_core/nightshift/queue.py; src/ego_data_core/nightshift/worker.py

**验收标准**
- 能创建 job，按 priority 和 created_at 拉取
- job 状态转换有审计记录
- 失败能记录 error_message 并按 max_retries 重试
- worker 可单进程运行，支持优雅停止

**测试**
- `pytest tests/nightshift/test_queue.py`

**给 Codex 的任务提示词**

```text
请实现 Night Shift 本地任务队列。基于 jobs 表提供 create_job、claim_next_job、mark_succeeded、mark_failed、mark_blocked、cancel_job。实现一个简单 worker 循环，可注册 job handler。所有状态变化写 audit。
```

### EDC-011｜Model Router 接口与 RuleBasedAdapter

- **里程碑**：M3 Enhancement Pipeline
- **优先级**：P0
- **模块**：model_router
- **依赖**：EDC-004
- **任务说明**：建立模型适配器接口，先实现 RuleBasedAdapter，保证没有外部模型也能跑通 Demo。
- **输入**：无
- **输出**：src/ego_data_core/model_router/base.py; src/ego_data_core/model_router/rule_based.py; src/ego_data_core/model_router/service.py

**验收标准**
- ModelRouter.run(purpose, input_refs, policy) 可返回结构化输出
- RuleBasedAdapter 支持 summary/tag/task_candidate/risk_candidate 基础输出
- 所有调用写 model_invocations
- 敏感/critical 数据默认不允许外部调用

**测试**
- `pytest tests/model_router/test_rule_based.py`

**给 Codex 的任务提示词**

```text
请实现 Model Router 最小版。定义 ModelAdapter 协议，先写 RuleBasedAdapter，不调用外部 API。它能基于文本 chunk 做简单摘要、关键词标签、待办候选、风险候选。每次调用写 model_invocations 和 audit。
```

### EDC-012｜OllamaAdapter 可选本地模型适配

- **里程碑**：M3 Enhancement Pipeline
- **优先级**：P1
- **模块**：model_router
- **依赖**：EDC-011
- **任务说明**：实现可选 Ollama 本地模型适配器，支持本地模型增强，但系统不能依赖它才能运行。
- **输入**：OLLAMA_BASE_URL; OLLAMA_MODEL
- **输出**：src/ego_data_core/model_router/ollama_adapter.py

**验收标准**
- Ollama 不存在时系统正常降级 RuleBasedAdapter
- 支持超时、错误记录、原始输出保存
- Prompt 不包含超出输入 refs 的数据
- 模型输出解析失败时保存原文并标记 error

**测试**
- `pytest tests/model_router/test_ollama_adapter.py`

**给 Codex 的任务提示词**

```text
请实现 OllamaAdapter。通过本地 HTTP 调用 Ollama generate/chat 接口，超时可配置。Ollama 不可用时不得影响主流程。所有输入必须来自 ModelRouter 传入的 input_refs，不允许自行读取 Vault 全量数据。
```

### EDC-013｜Enhancement Pipeline：summary/tag

- **里程碑**：M3 Enhancement Pipeline
- **优先级**：P0
- **模块**：twin
- **依赖**：EDC-008, EDC-010, EDC-011
- **任务说明**：对 Evidence 生成摘要和标签，写 enhancements 与 evidence 链接。
- **输入**：evidence_ids
- **输出**：src/ego_data_core/twin/enhance.py; POST /api/v1/twin/enhance

**验收标准**
- POST /twin/enhance 创建 job
- worker 执行后写 enhancements
- 每个 enhancement 必须链接至少一个 evidence
- 记录 model_invocation_id、prompt_hash、confidence、status
- 可查询 evidence 的 enhancement 列表

**测试**
- `pytest tests/twin/test_enhance_summary_tag.py`

**给 Codex 的任务提示词**

```text
请实现 Enhancement Pipeline 最小版。支持 enhancement_type=summary/tag。API 创建 job，worker 读取 evidence_text_chunks，调用 ModelRouter，写 enhancements 与 enhancement_evidence_links。必须保持 evidence-first，可追溯。
```

### EDC-014｜Project Discovery v0

- **里程碑**：M4 Work Graph
- **优先级**：P1
- **模块**：workgraph
- **依赖**：EDC-013
- **任务说明**：基于目录、文件名、标签和摘要生成项目候选，允许用户确认/驳回。
- **输入**：raw_objects; enhancements
- **输出**：src/ego_data_core/workgraph/project_discovery.py; POST /api/v1/projects/discover

**验收标准**
- 能生成 project candidates 并写 projects 表或候选状态
- 能把 evidence 链接到 project
- 用户可 confirm/reject/edit
- 被驳回项目不应反复出现，除非 force_regenerate

**测试**
- `pytest tests/workgraph/test_project_discovery.py`

**给 Codex 的任务提示词**

```text
请实现 Project Discovery v0。使用规则优先：目录名、文件名前缀、标签相似度、日期聚类。生成项目候选并链接 evidence。提供用户反馈接口 confirm/reject/edit。不要把模型推断当事实，所有项目关系标记 confidence。
```

### EDC-015｜Task / Question / Risk 提取 v0

- **里程碑**：M4 Work Graph
- **优先级**：P1
- **模块**：workgraph
- **依赖**：EDC-013, EDC-014
- **任务说明**：从增强数据和文本块中提取待办、未决问题、风险项，全部保持证据链接。
- **输入**：enhancements; evidence_text_chunks
- **输出**：src/ego_data_core/workgraph/extractors.py

**验收标准**
- 能生成 tasks/questions/risks
- 每个对象至少关联一个 evidence
- 状态默认为 proposed，用户确认后变 confirmed
- 支持 feedback：confirm/reject/edit/later/convert_to_task

**测试**
- `pytest tests/workgraph/test_extractors.py`

**给 Codex 的任务提示词**

```text
请实现 Task/Question/Risk 提取 v0。先用规则和 RuleBasedAdapter，从文本中发现“需要/待/风险/问题/不确定/下一步”等线索。写入对应表，并建立 evidence_links。输出必须带 confidence 和 proposed 状态。
```

### EDC-016｜Automation Opportunity 发现 v0

- **里程碑**：M4 Work Graph
- **优先级**：P2
- **模块**：workgraph/operator
- **依赖**：EDC-015
- **任务说明**：基于文件变化、重复文件模式和用户反馈生成低风险自动化机会。
- **输入**：raw_objects; events; tasks
- **输出**：src/ego_data_core/workgraph/automation_opportunities.py

**验收标准**
- 能生成 automation_opportunities
- 每个机会包含风险等级、建议动作、所需授权
- 默认只生成建议，不执行
- 移动/删除/发送/上传类建议必须标记 high risk

**测试**
- `pytest tests/workgraph/test_automation_opportunities.py`

**给 Codex 的任务提示词**

```text
请实现自动化机会发现 v0。先发现重复文件、待整理下载目录、同项目文件分散等低风险机会。只生成 action proposal，不直接执行。所有建议都要写 evidence link、risk_level、required_authorization。
```

### EDC-017｜Daily Brief 生成器 v0

- **里程碑**：M5 Daily Brief
- **优先级**：P0
- **模块**：brief
- **依赖**：EDC-013, EDC-015
- **任务说明**：按日期生成 Ego Daily Brief，包含新增资料、项目动态、待办、问题、风险、自动化建议。
- **输入**：evidence; enhancements; projects; tasks; questions; risks; automation_opportunities
- **输出**：src/ego_data_core/brief/daily.py; POST /briefs/generate; GET /briefs/daily/latest

**验收标准**
- 能按日期生成 report 和 report_items
- 每个 report_item 必须至少有一个 evidence 或 system audit reference，纯系统项除外
- Brief 可导出 Markdown 到 vault://briefs
- 用户可对 item 反馈 confirm/reject/later/convert_to_task
- 没有足够数据时生成清晰的数据健康提示，而不是编造内容

**测试**
- `pytest tests/brief/test_daily_brief.py`

**给 Codex 的任务提示词**

```text
请实现 Daily Brief 生成器 v0。输入 date，聚合当天新增 evidence、summary/tag、tasks/questions/risks、automation_opportunities。生成 report/report_items 并导出 Markdown。原则：没有证据就不写结论；不确定则用“可能/建议核对”。
```

### EDC-018｜Markdown 导出器与证据引用格式

- **里程碑**：M5 Daily Brief
- **优先级**：P0
- **模块**：brief/vault
- **依赖**：EDC-017, EDC-007
- **任务说明**：将 Brief、Project Brief 导出为 Markdown，并用稳定格式引用 Evidence。
- **输入**：reports; report_items; evidence_links
- **输出**：src/ego_data_core/brief/export_markdown.py

**验收标准**
- 导出文件包含 title、date、summary、sections、evidence references
- 证据引用格式统一为 [ev_xxx] title/path/time
- 不暴露敏感绝对路径，除非本地 UI 用户主动展开
- 导出文件写入 vault://briefs

**测试**
- `pytest tests/brief/test_markdown_export.py`

**给 Codex 的任务提示词**

```text
请实现 Brief Markdown 导出。输出每日简报，要求每个条目带证据引用，如 Evidence: [ev_...] 文件名 · 时间 · 摘要。不要在 Markdown 中直接泄露用户绝对路径，可显示相对标签或标题。
```

### EDC-019｜本地 Web UI 最小版

- **里程碑**：M5 Daily Brief
- **优先级**：P1
- **模块**：ui
- **依赖**：EDC-017, EDC-005, EDC-009
- **任务说明**：提供本地浏览器界面查看 Sources、Evidence、Search、Daily Brief、Audit。
- **输入**：Local API
- **输出**：ui/ 或 src/ego_data_core/ui/static

**验收标准**
- 打开 http://127.0.0.1:8765 可看到本地 UI
- 可查看最新 Daily Brief
- 可查看 Evidence 列表与搜索
- 可查看审计日志
- 界面明确显示 Local-first 与数据源授权状态

**测试**
- `pytest tests/api/test_static_ui.py 或 Playwright smoke test`

**给 Codex 的任务提示词**

```text
请实现本地 Web UI 最小版。可以使用 FastAPI 静态页面 + 原生 JS，不必引入复杂前端框架。页面包含：Dashboard、Sources、Search、Brief、Audit。UI 只连接本地 API。
```

### EDC-020｜Safety Kernel：隐私等级与外部调用策略

- **里程碑**：M3 Enhancement Pipeline
- **优先级**：P0
- **模块**：safety
- **依赖**：EDC-011, EDC-004
- **任务说明**：根据 public/private/sensitive/critical 决定模型调用、上下文输出和动作授权。
- **输入**：privacy_level; policy_json
- **输出**：src/ego_data_core/safety/policy.py

**验收标准**
- critical 默认禁止模型读取，除非显式逐次授权
- sensitive 默认仅本地模型/规则
- private 默认本地，外部需策略允许
- public 可外部处理但仍需记录
- 策略拦截写 policy_blocked audit

**测试**
- `pytest tests/safety/test_policy.py`

**给 Codex 的任务提示词**

```text
请实现 Safety Kernel 的隐私策略判断。提供 can_use_external_model、can_include_evidence_in_context、requires_authorization。严格遵守 critical/sensitive/private/public 默认策略。任何阻断写 audit。
```

### EDC-021｜Operator Bridge：Action Plan Dry-run

- **里程碑**：M6 Operator Bridge + Demo
- **优先级**：P1
- **模块**：operator
- **依赖**：EDC-016, EDC-020
- **任务说明**：预留物理操作执行接口，v0.1 先支持 Action Plan、授权和 dry_run，不真正操作电脑。
- **输入**：automation_opportunities
- **输出**：src/ego_data_core/operator/bridge.py; actions API

**验收标准**
- POST /actions/propose 可创建 action_plan
- 授权前 execute 返回 requires_authorization
- dry_run 生成步骤和风险说明
- 高风险动作必须用户授权
- 所有 propose/authorize/execute 写 audit

**测试**
- `pytest tests/operator/test_action_dry_run.py`

**给 Codex 的任务提示词**

```text
请实现 Operator Bridge dry-run。它不实际控制电脑，只生成 action_plan、required_authorization、dry_run_steps。实现 /actions/propose、/actions/{id}/authorize、/actions/{id}/execute。没有授权不得执行。
```

### EDC-022｜屏幕采集 Connector v0：手动截图入库

- **里程碑**：M6 Operator Bridge + Demo
- **优先级**：P1
- **模块**：connectors/screen
- **依赖**：EDC-005, EDC-007
- **任务说明**：v0.1 先实现手动上传/本机截图导入，生成 screenshot evidence，为未来 HDMI 采集预留接口。
- **输入**：image file or screenshot API
- **输出**：src/ego_data_core/connectors/screen/capture.py

**验收标准**
- 可通过 API 或 CLI 导入 screenshot
- 生成 raw_object/object_version/evidence，evidence_type=screenshot
- 记录 active_window/app_name 可选 metadata
- 不做全天候录屏

**测试**
- `pytest tests/connectors/test_screen_capture.py`

**给 Codex 的任务提示词**

```text
请实现屏幕采集 Connector v0。先支持导入已有图片文件作为 screenshot evidence；可选支持 PIL/ImageGrab 在桌面环境截图。为 HDMI 采集保留接口类，但不要实现设备驱动。
```

### EDC-023｜Screenshot OCR Enhancement v0

- **里程碑**：M6 Operator Bridge + Demo
- **优先级**：P1
- **模块**：twin/screen
- **依赖**：EDC-022, EDC-013
- **任务说明**：对 screenshot evidence 生成 OCR 文本增强，先支持可选 OCR；OCR 不可用时生成占位 enhancement。
- **输入**：screenshot evidence
- **输出**：ocr_text enhancement; screen_state enhancement

**验收标准**
- 支持 OCR adapter 接口
- 没有 OCR 环境时不崩溃，写 unsupported 状态
- OCR 输出必须链接 screenshot evidence
- 保留坐标/区域 metadata 结构

**测试**
- `pytest tests/twin/test_screenshot_ocr.py`

**给 Codex 的任务提示词**

```text
请实现 Screenshot OCR Enhancement v0。定义 OCRAdapter 接口，可先写 MockOCRAdapter 或 EasyOCR/PaddleOCR 可选适配。OCR 输出写 enhancement，包含 text 和可选 boxes。不可用时写 status=unsupported，不影响其他流程。
```

### EDC-024｜Compute Fabric 节点注册 v0

- **里程碑**：M6 Operator Bridge + Demo
- **优先级**：P2
- **模块**：compute_fabric
- **依赖**：EDC-001
- **任务说明**：注册本机、局域网服务器、外部模型节点的能力信息，为后续分层调度打基础。
- **输入**：devices; compute_nodes
- **输出**：src/ego_data_core/compute_fabric/nodes.py; GET/POST /compute/nodes

**验收标准**
- 可手动注册 compute node
- 记录 CPU/GPU/NPU/内存/模型/信任等级/能耗估算
- Model Router 可读取节点能力
- 外部节点默认不可处理 sensitive/critical

**测试**
- `pytest tests/compute_fabric/test_nodes.py`

**给 Codex 的任务提示词**

```text
请实现 Compute Fabric 节点注册 v0。可手动注册本机、本地服务器、外部 API 节点，记录 capabilities_json、trust_level、cost_profile、energy_profile。暂不实现自动发现。
```

### EDC-025｜CLI 工具：扫描、增强、生成 Brief

- **里程碑**：M5 Daily Brief
- **优先级**：P1
- **模块**：cli
- **依赖**：EDC-006, EDC-013, EDC-017
- **任务说明**：提供无需 UI 的命令行入口，方便测试与演示。
- **输入**：无
- **输出**：src/ego_data_core/cli.py

**验收标准**
- ego init-db
- ego source add <path>
- ego scan <source_id>
- ego enhance --date YYYY-MM-DD
- ego brief daily --date YYYY-MM-DD
- 命令失败返回非零 exit code 并写日志

**测试**
- `pytest tests/cli/test_cli.py`

**给 Codex 的任务提示词**

```text
请实现 CLI。使用 typer 或 argparse。提供 init-db、source add、scan、enhance、brief daily、audit tail。CLI 用于本地 Demo，所有命令调用同一 service 层，不绕过业务逻辑。
```

### EDC-026｜Demo Seed 数据与一键演示脚本

- **里程碑**：M6 Operator Bridge + Demo
- **优先级**：P0
- **模块**：demo
- **依赖**：EDC-017, EDC-025
- **任务说明**：构造可公开展示的样例数据，一键跑通扫描、增强、Work Graph、Daily Brief。
- **输入**：sample_docs/
- **输出**：demo/sample_workspace/; scripts/run_demo.sh; docs/demo_script.md

**验收标准**
- 全新环境执行 scripts/run_demo.sh 可生成 Daily Brief
- Demo 数据不包含真实隐私
- 输出 Brief 中每个条目都有 Evidence 引用
- 5 分钟内可以演示产品核心闭环

**测试**
- `bash scripts/run_demo.sh`
- `pytest tests/demo/test_demo_smoke.py`

**给 Codex 的任务提示词**

```text
请创建 Demo Seed 数据和一键演示脚本。构造一个 sample_workspace，包含 Ego 项目计划、会议纪要、报价草案、待办清单、重复文件。run_demo.sh 完成 init-db、add source、scan、enhance、discover、brief，最后打印 Brief Markdown 路径。
```

### EDC-027｜数据健康检查 Data Health

- **里程碑**：M5 Daily Brief
- **优先级**：P2
- **模块**：brief/data_health
- **依赖**：EDC-017
- **任务说明**：在 Daily Brief 中加入数据覆盖度、解析失败、未增强证据、隐私阻断等系统健康信息。
- **输入**：jobs; evidence; enhancements; audit
- **输出**：data_health report_items

**验收标准**
- 显示新增文件数量、解析成功率、增强完成率
- 显示失败 job 和可重试建议
- 显示被隐私策略阻断的外部调用次数
- 没有数据时给出下一步配置建议

**测试**
- `pytest tests/brief/test_data_health.py`

**给 Codex 的任务提示词**

```text
请实现 Data Health 汇报项。Daily Brief 中加入系统状态：新增 evidence 数、解析失败数、enhancement 完成率、policy_blocked 数、待处理 job 数、建议用户新增数据源或授权。
```

### EDC-028｜错误处理与日志规范

- **里程碑**：M0 Project Foundation
- **优先级**：P0
- **模块**：kernel/logging
- **依赖**：EDC-000, EDC-004
- **任务说明**：统一异常类型、日志格式和错误响应，避免后台任务静默失败。
- **输入**：无
- **输出**：src/ego_data_core/kernel/errors.py; src/ego_data_core/kernel/logging.py

**验收标准**
- API 错误返回稳定 JSON：code/message/request_id
- 后台 job 错误写 jobs.error_message 和 audit
- 日志不输出完整敏感文本，只输出 ID/摘要
- 有全局 FastAPI exception handler

**测试**
- `pytest tests/kernel/test_errors.py`

**给 Codex 的任务提示词**

```text
请实现统一错误处理与日志。定义 EgoError 基类和子类：PolicyBlockedError、NotFoundError、ValidationError、ConnectorError、ModelError、StorageError。API 返回稳定 JSON。日志中避免输出用户原文内容。
```

### EDC-029｜测试基座与临时工作区 Fixture

- **里程碑**：M0 Project Foundation
- **优先级**：P0
- **模块**：tests
- **依赖**：EDC-000, EDC-001
- **任务说明**：建立 pytest fixture：临时 EGO_DATA_HOME、内存/临时 SQLite、样例文件、测试客户端。
- **输入**：无
- **输出**：tests/conftest.py; tests/fixtures/

**验收标准**
- 每个测试用例隔离数据目录
- 测试不会读写用户真实目录
- API TestClient 可复用
- 提供 sample txt/md/docx/pdf 或可跳过 pdf/docx 依赖

**测试**
- `pytest`

**给 Codex 的任务提示词**

```text
请建立 pytest 测试基座。conftest 提供 tmp_data_home、db_path、client、sample_workspace fixtures。所有测试必须使用临时目录，严禁读写真实用户目录。
```

### EDC-030｜OpenAPI 同步与契约测试

- **里程碑**：M6 Operator Bridge + Demo
- **优先级**：P1
- **模块**：api
- **依赖**：EDC-017, EDC-021
- **任务说明**：确保实现 API 与 openapi.yaml 草案一致，并生成本地 OpenAPI 文档。
- **输入**：ego_data_core_v0_1_openapi.yaml
- **输出**：docs/api_contract.md; tests/api/test_openapi_contract.py

**验收标准**
- FastAPI /openapi.json 可访问
- 核心路径与草案一致或有差异说明
- 契约测试覆盖 health/sources/vault/twin/briefs/actions/audit
- README 标明 API 仍为 v0.1 local API

**测试**
- `pytest tests/api/test_openapi_contract.py`

**给 Codex 的任务提示词**

```text
请实现 OpenAPI 契约测试。读取现有草案，校验实现中的核心路径存在。若字段不完全一致，在 docs/api_contract.md 中列差异和原因。FastAPI 自动生成 /openapi.json。
```


---

## 8. 端到端测试场景

### E2E-01：空系统启动

步骤：

1. 创建临时 `EGO_DATA_HOME`；
2. 启动 API；
3. 调用 `/api/v1/health`；
4. 查询 `/api/v1/audit/logs`。

通过标准：

- API 正常；
- DB 初始化成功；
- Audit 表可查询；
- 不访问任何用户真实目录。

### E2E-02：文件夹扫描入库

步骤：

1. 创建 sample workspace；
2. POST `/sources` 创建 filesystem source；
3. 调用 scan job；
4. 查询 Evidence。

通过标准：

- 每个样例文件生成 raw_object、version、evidence；
- 用户原目录文件 hash 不变；
- 扫描过程写 audit。

### E2E-03：文档解析与检索

步骤：

1. 对 sample workspace 执行 parse job；
2. 搜索一个样例关键词；
3. 查看返回 chunk。

通过标准：

- 文本块存在；
- 搜索结果包含 evidence_id；
- 解析失败项不影响其他文件。

### E2E-04：增强流水线

步骤：

1. 对若干 Evidence 创建 summary/tag enhancement job；
2. worker 执行；
3. 查询 enhancement。

通过标准：

- Enhancement 写入成功；
- 与 Evidence 建立 link；
- model_invocations 记录存在；
- RuleBasedAdapter 无外部依赖。

### E2E-05：Daily Brief

步骤：

1. 执行 project discovery；
2. 执行 task/risk/question extraction；
3. 生成 Daily Brief；
4. 导出 Markdown。

通过标准：

- Brief 存在；
- Markdown 存在；
- 每个事实条目有 Evidence 引用；
- 不足信息被标记为 Data Health，而不是编造。

### E2E-06：Action dry-run

步骤：

1. 基于自动化机会创建 action proposal；
2. 未授权执行；
3. 授权后执行 dry-run。

通过标准：

- 未授权时拒绝执行；
- 授权记录写入；
- dry-run 输出动作步骤；
- 不实际修改用户文件。

---

## 9. 5 分钟 Demo 脚本

### 演示目标

证明 Ego Data Core 不是聊天机器人，而是一个持续运行的个人数据操作系统。

### 演示素材

`demo/sample_workspace/` 包含：

- `Ego项目路线讨论.md`
- `投资人方案草稿.md`
- `硬件采购清单.md`
- `会议纪要_20260528.md`
- `待办清单.txt`
- `重复资料/Ego项目路线讨论_copy.md`

### 演示流程

1. 打开本地 UI 或终端；
2. 添加 sample workspace 为 Source；
3. 执行扫描，展示 Evidence 入库；
4. 执行增强，展示摘要和标签；
5. 执行 Work Graph，展示项目、任务、问题、风险；
6. 生成 Daily Brief；
7. 点击一个 Brief 条目，展开证据来源；
8. 展示一个自动化机会：例如“重复资料清理建议”；
9. 点击 dry-run，展示动作计划；
10. 展示 Audit Log。

### 演示金句

> Ego 不压缩替代你的记忆，而是保存原始证据，并持续生成可追溯的增强数据。  
> Ego 不是等你提问，而是在你不使用电脑时继续工作。  
> Ego 现在先整理数据，下一步通过硬件 Operator 执行动作。

---

## 10. 质量门禁

每个里程碑合并前必须满足：

1. `pytest` 通过；
2. Demo 数据不包含真实隐私；
3. 不修改用户原始目录；
4. 所有外部调用默认关闭；
5. 所有数据变更写 Audit；
6. 所有模型输出可追溯 Evidence；
7. 所有高风险动作只 dry-run；
8. README 更新。

---

## 11. 风险与应对

| 风险 | 表现 | 应对 |
|---|---|---|
| 范围失控 | 想同时做手机、微信、感知硬件、Operator | v0.1 只做 PC 文件 + 手动截图 + Daily Brief |
| 模型依赖过强 | 没有本地模型就跑不起来 | RuleBasedAdapter P0，Ollama P1 |
| 数据幻觉 | Brief 编造结论 | 每个条目强制 Evidence link，无证据则写 data_health |
| 隐私风险 | 外部模型读取敏感文件 | Safety Kernel 默认阻断 sensitive/critical |
| 文件破坏 | 自动整理误删用户文件 | v0.1 严禁真实执行，只 dry-run |
| Codex 一次写太多 | 代码不可控、测试缺失 | 每次只做一个 Issue，每个 Issue 必须有测试 |
| UI 过早复杂化 | 工程资源被前端消耗 | UI P1，CLI + Markdown 导出优先 |
| schema 演进困难 | 前期表设计不适配 | Enhancement 可重算；Schema v0.1 先服务闭环，不追求完美 |

---

## 12. 版本结束定义 Definition of Done

Ego Data Core v0.1 完成的标准：

1. 用户可以通过 CLI 或本地 UI 添加一个本地目录；
2. 系统只读扫描目录并建立 Vault；
3. 系统生成 Raw Object、Version、Evidence；
4. 系统解析文档文本并分块；
5. 系统生成 summary/tag 等增强数据；
6. 系统发现项目、任务、问题和风险候选；
7. 系统生成一份 Daily Brief；
8. Brief 中关键结论可以回溯 Evidence；
9. 用户可以反馈条目；
10. 系统可以提出低风险自动化机会；
11. Action 只支持授权与 dry-run；
12. Audit Log 完整记录主要操作；
13. 一键 Demo 可以在干净环境跑通；
14. 不依赖云端模型即可完成最小闭环。

---

## 13. 给开发负责人的执行建议

第一周只做 M0 + M1 的最小闭环，不要碰模型。

最早可演示版本的顺序应为：

```text
EDC-000 → EDC-001 → EDC-002 → EDC-003 → EDC-028 → EDC-029
  ↓
EDC-004 → EDC-005 → EDC-006 → EDC-007
  ↓
EDC-008 → EDC-010 → EDC-011 → EDC-013
  ↓
EDC-017 → EDC-018 → EDC-026
```

这一条链跑通后，就已经能证明 Ego Data Core 的基本价值。

不要把时间优先花在：

- 漂亮 UI；
- 复杂 Agent；
- 复杂多模型路由；
- 手机数据；
- 自动控制电脑；
- 分布式算力网络；
- 专用硬件。

v0.1 的胜负手只有一个：

> **用户第二天打开 Ego，看到一份准确、有证据、有帮助的主动工作报告。**
