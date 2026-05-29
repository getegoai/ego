# Ego Data Core v0.1 Codex Prompt Pack

本文件用于把开发任务逐个投喂给 Codex。每次只复制一个任务块，不要一次性复制全文件。

---

## 通用上下文

你正在开发 `ego-data-core`。项目目标是本地优先、证据优先的个人数据操作系统。v0.1 只做：本地文件扫描、Evidence 入库、增强数据、Work Graph、Daily Brief、Action dry-run 和 Audit。

不可违反的原则：

1. 不修改用户原始文件；
2. 不默认调用云端模型；
3. 不把摘要当原始记忆；
4. 所有关键结论可追溯 Evidence；
5. 所有数据变更写 Audit；
6. 高风险动作只 dry-run，必须授权。

---


## EDC-000｜建立仓库骨架与工程约束

```text
任务：EDC-000｜建立仓库骨架与工程约束

背景：
Ego Data Core v0.1 是本地优先、证据优先的个人数据操作系统。请只实现本 Issue，不扩展到无关功能。

模块：repo
依赖：无

任务说明：
创建 ego-data-core Python/FastAPI 项目骨架，固定目录结构、依赖管理、基础配置和开发命令。

具体要求：
请创建 ego-data-core 的 Python 3.11 + FastAPI 项目骨架。使用 src layout，保留清晰模块边界：api、kernel、storage、connectors、vault、twin、workgraph、brief、nightshift、model_router、compute_fabric、operator、safety、audit。先实现 /api/v1/health，加入 README、.env.example 和基础 pytest。

验收标准：
1. python -m ego_data_core.main 或 uvicorn ego_data_core.api.app:app 可启动本地 API
2. GET /api/v1/health 返回 ok、版本号、数据库状态
3. README 中包含本地启动、初始化数据库、运行测试的命令
4. 不得创建任何会修改用户原始文件的逻辑

必须新增或更新测试：
- pytest tests/test_health.py

限制：
- 不要修改用户原始目录；
- 不要默认访问网络；
- 不要绕过 Audit；
- 不要把模型生成内容写成 Evidence；
- 不要实现本 Issue 以外的大量功能。
```


## EDC-001｜SQLite 初始化与迁移管理

```text
任务：EDC-001｜SQLite 初始化与迁移管理

背景：
Ego Data Core v0.1 是本地优先、证据优先的个人数据操作系统。请只实现本 Issue，不扩展到无关功能。

模块：storage
依赖：EDC-000

任务说明：
接入现有 SQLite Schema，建立本地数据库初始化、迁移执行、连接管理和事务封装。

具体要求：
请实现 SQLite 初始化与迁移系统。把现有 schema 放入 storage/migrations/001_init.sql；提供 get_connection、transaction、run_migrations。所有连接开启 foreign_keys。写 pytest 验证 schema 可创建、关键表存在、重复迁移安全。

验收标准：
1. 首次启动可自动创建数据库
2. PRAGMA foreign_keys = ON
3. schema 全部表可创建成功
4. 重复执行迁移不破坏已有数据

必须新增或更新测试：
- pytest tests/storage/test_db_init.py

限制：
- 不要修改用户原始目录；
- 不要默认访问网络；
- 不要绕过 Audit；
- 不要把模型生成内容写成 Evidence；
- 不要实现本 Issue 以外的大量功能。
```


## EDC-002｜统一 ID 生成器

```text
任务：EDC-002｜统一 ID 生成器

背景：
Ego Data Core v0.1 是本地优先、证据优先的个人数据操作系统。请只实现本 Issue，不扩展到无关功能。

模块：kernel
依赖：EDC-000

任务说明：
实现带前缀、日期和随机/ULID 后缀的统一对象 ID，覆盖 User、Device、Source、Object、Evidence、Job 等核心实体。

具体要求：
请实现统一 ID 生成器。格式建议 prefix_YYYYMMDD_<ulid_or_secure_random>。要求可测试、无全局状态污染、非法前缀报错。为所有 v0.1 实体预置允许前缀，并写碰撞测试。

验收标准：
1. 支持 usr/dev/src/obj/ver/ev/chk/enh/proj/task/q/risk/auto/brief/job/mi/act/aud/report/item 等前缀
2. ID 可排序或至少可按日期识别
3. 10 万次生成无碰撞
4. 非法前缀会抛出明确异常

必须新增或更新测试：
- pytest tests/kernel/test_id_generator.py

限制：
- 不要修改用户原始目录；
- 不要默认访问网络；
- 不要绕过 Audit；
- 不要把模型生成内容写成 Evidence；
- 不要实现本 Issue 以外的大量功能。
```


## EDC-003｜配置系统与本地目录规范

```text
任务：EDC-003｜配置系统与本地目录规范

背景：
Ego Data Core v0.1 是本地优先、证据优先的个人数据操作系统。请只实现本 Issue，不扩展到无关功能。

模块：kernel
依赖：EDC-000

任务说明：
建立 Ego 本地工作目录、Vault 目录、日志目录、模型配置、隐私策略配置。

具体要求：
请实现配置系统。使用 pydantic-settings 或等价轻量方案。默认 EGO_DATA_HOME=~/.ego_data_core，可用环境变量覆盖。启动时创建 vault 子目录：objects、versions、evidence、extracted_text、model_outputs、briefs、logs、tmp。

验收标准：
1. 默认数据目录为用户主目录下 .ego_data_core 或环境变量 EGO_DATA_HOME
2. Vault、extracted_text、model_outputs、briefs、logs、tmp 目录自动创建
3. 配置项不包含硬编码绝对路径
4. 配置支持 dev/test/prod 三类 profile

必须新增或更新测试：
- pytest tests/kernel/test_config.py

限制：
- 不要修改用户原始目录；
- 不要默认访问网络；
- 不要绕过 Audit；
- 不要把模型生成内容写成 Evidence；
- 不要实现本 Issue 以外的大量功能。
```


## EDC-004｜Audit Log 最小实现

```text
任务：EDC-004｜Audit Log 最小实现

背景：
Ego Data Core v0.1 是本地优先、证据优先的个人数据操作系统。请只实现本 Issue，不扩展到无关功能。

模块：audit
依赖：EDC-001, EDC-002

任务说明：
所有采集、增强、模型调用、策略拦截、用户授权与错误必须写入审计日志。

具体要求：
请实现 AuditService。提供追加审计日志和分页查询。事件类型包括 source_created、object_ingested、evidence_created、job_created、model_invoked、policy_blocked、brief_generated、action_authorized、error。不要实现删除审计日志的业务接口。

验收标准：
1. 提供 append_audit_log(event_type, actor, target, payload) 方法
2. 审计记录不可被普通业务代码更新，只允许追加
3. GET /api/v1/audit/logs 可分页查询
4. 错误也必须可写 audit

必须新增或更新测试：
- pytest tests/audit/test_audit_service.py

限制：
- 不要修改用户原始目录；
- 不要默认访问网络；
- 不要绕过 Audit；
- 不要把模型生成内容写成 Evidence；
- 不要实现本 Issue 以外的大量功能。
```


## EDC-005｜Source 管理 API

```text
任务：EDC-005｜Source 管理 API

背景：
Ego Data Core v0.1 是本地优先、证据优先的个人数据操作系统。请只实现本 Issue，不扩展到无关功能。

模块：api/connectors
依赖：EDC-001, EDC-004

任务说明：
实现数据源创建、列表、启用/停用和隐私等级配置。

具体要求：
请实现 Source 管理 API。严格按 OpenAPI 草案实现 GET/POST /api/v1/sources，字段包括 source_type、name、root_uri、privacy_level、scan_policy、retention_policy。写入数据库 sources 表，并写 audit。

验收标准：
1. POST /sources 可创建 filesystem/screen/browser/manual source
2. GET /sources 返回 source 列表
3. 创建时写 audit
4. 默认 privacy_level=private

必须新增或更新测试：
- pytest tests/api/test_sources.py

限制：
- 不要修改用户原始目录；
- 不要默认访问网络；
- 不要绕过 Audit；
- 不要把模型生成内容写成 Evidence；
- 不要实现本 Issue 以外的大量功能。
```


## EDC-006｜文件系统扫描器 v0

```text
任务：EDC-006｜文件系统扫描器 v0

背景：
Ego Data Core v0.1 是本地优先、证据优先的个人数据操作系统。请只实现本 Issue，不扩展到无关功能。

模块：connectors/filesystem
依赖：EDC-005, EDC-002, EDC-003

任务说明：
扫描指定目录，计算文件哈希，生成 Raw Object、Object Version 和 Evidence。不得修改用户原目录。

具体要求：
请实现只读文件系统扫描器。输入 source_id，读取 sources.root_uri 和 scan_policy_json。递归扫描常见文档文件，计算 sha256，复制版本到 Ego Vault 的 versions 目录，写 raw_objects、object_versions、evidence。严禁修改用户原目录。

验收标准：
1. 支持递归扫描，可配置 max_depth、include/exclude glob
2. 计算 sha256、文件大小、mtime、mime type
3. 新文件生成 raw_objects、object_versions、evidence
4. 同 hash 文件不重复复制，或能标记重复关系
5. 扫描过程只读，不移动、不改名、不删除用户文件

必须新增或更新测试：
- pytest tests/connectors/test_filesystem_scanner.py

限制：
- 不要修改用户原始目录；
- 不要默认访问网络；
- 不要绕过 Audit；
- 不要把模型生成内容写成 Evidence；
- 不要实现本 Issue 以外的大量功能。
```


## EDC-007｜Vault 文件存储与 URI 规范

```text
任务：EDC-007｜Vault 文件存储与 URI 规范

背景：
Ego Data Core v0.1 是本地优先、证据优先的个人数据操作系统。请只实现本 Issue，不扩展到无关功能。

模块：vault
依赖：EDC-003, EDC-006

任务说明：
定义 vault:// URI 映射到本地文件系统，封装对象版本、证据、文本、模型输出的读写路径。

具体要求：
请实现 VaultStorage。定义 vault:// URI 到 EGO_DATA_HOME/vault 的映射，支持安全复制文件、写 JSON、写文本、读取文本、校验 URI。必须防止 ../ 路径穿越，不能把用户原始绝对路径作为 Vault 文件名。

验收标准：
1. 支持 vault://objects、vault://versions、vault://evidence、vault://extracted_text、vault://model_outputs、vault://briefs
2. 所有写入路径防止目录穿越
3. 提供 resolve_uri 与 safe_write_json/safe_write_text/safe_copy_file
4. 文件名中不直接暴露用户敏感原路径

必须新增或更新测试：
- pytest tests/vault/test_storage_uri.py

限制：
- 不要修改用户原始目录；
- 不要默认访问网络；
- 不要绕过 Audit；
- 不要把模型生成内容写成 Evidence；
- 不要实现本 Issue 以外的大量功能。
```


## EDC-008｜文档解析器 v0：txt/md/pdf/docx

```text
任务：EDC-008｜文档解析器 v0：txt/md/pdf/docx

背景：
Ego Data Core v0.1 是本地优先、证据优先的个人数据操作系统。请只实现本 Issue，不扩展到无关功能。

模块：connectors/documents
依赖：EDC-006, EDC-007

任务说明：
对 Object Version 提取文本，生成 extracted_text_uri 和 evidence_text_chunks。

具体要求：
请实现文档解析器 v0。先支持 txt/md/pdf/docx。可用 pypdf、python-docx 等轻量库；库不可用时要优雅降级。把抽取文本写到 vault://extracted_text，并按 800-1200 字符分块写 evidence_text_chunks。

验收标准：
1. 支持 .txt、.md、.pdf、.docx 基础文本提取
2. 解析失败不得中断扫描，写 error audit 与 job failure
3. 按段落/长度分块写 evidence_text_chunks
4. chunk 记录 evidence_id、chunk_index、text、char_start/char_end 或 metadata

必须新增或更新测试：
- pytest tests/connectors/test_document_parser.py

限制：
- 不要修改用户原始目录；
- 不要默认访问网络；
- 不要绕过 Audit；
- 不要把模型生成内容写成 Evidence；
- 不要实现本 Issue 以外的大量功能。
```


## EDC-009｜全文检索最小实现

```text
任务：EDC-009｜全文检索最小实现

背景：
Ego Data Core v0.1 是本地优先、证据优先的个人数据操作系统。请只实现本 Issue，不扩展到无关功能。

模块：vault/search
依赖：EDC-008

任务说明：
基于 SQLite FTS5 或降级 LIKE 实现本地文本搜索，支持按 evidence、source、date 过滤。

具体要求：
请实现本地全文检索。优先使用 SQLite FTS5 建立 evidence_chunks_fts；若环境不支持 FTS5，降级为 LIKE 搜索。新增 GET /api/v1/search?q=。返回 evidence_id、chunk_id、snippet、title、captured_at。

验收标准：
1. 能按关键词返回 chunk、evidence_id、raw_object title、score 或匹配信息
2. 支持 source_id 和日期过滤
3. 返回结果不直接暴露未授权路径
4. FTS5 不可用时有降级方案

必须新增或更新测试：
- pytest tests/vault/test_search.py

限制：
- 不要修改用户原始目录；
- 不要默认访问网络；
- 不要绕过 Audit；
- 不要把模型生成内容写成 Evidence；
- 不要实现本 Issue 以外的大量功能。
```


## EDC-010｜Night Shift Job Queue v0

```text
任务：EDC-010｜Night Shift Job Queue v0

背景：
Ego Data Core v0.1 是本地优先、证据优先的个人数据操作系统。请只实现本 Issue，不扩展到无关功能。

模块：nightshift
依赖：EDC-001, EDC-004

任务说明：
实现 SQLite 驱动的本地任务队列，支持 pending/running/succeeded/failed/blocked/cancelled 和重试。

具体要求：
请实现 Night Shift 本地任务队列。基于 jobs 表提供 create_job、claim_next_job、mark_succeeded、mark_failed、mark_blocked、cancel_job。实现一个简单 worker 循环，可注册 job handler。所有状态变化写 audit。

验收标准：
1. 能创建 job，按 priority 和 created_at 拉取
2. job 状态转换有审计记录
3. 失败能记录 error_message 并按 max_retries 重试
4. worker 可单进程运行，支持优雅停止

必须新增或更新测试：
- pytest tests/nightshift/test_queue.py

限制：
- 不要修改用户原始目录；
- 不要默认访问网络；
- 不要绕过 Audit；
- 不要把模型生成内容写成 Evidence；
- 不要实现本 Issue 以外的大量功能。
```


## EDC-011｜Model Router 接口与 RuleBasedAdapter

```text
任务：EDC-011｜Model Router 接口与 RuleBasedAdapter

背景：
Ego Data Core v0.1 是本地优先、证据优先的个人数据操作系统。请只实现本 Issue，不扩展到无关功能。

模块：model_router
依赖：EDC-004

任务说明：
建立模型适配器接口，先实现 RuleBasedAdapter，保证没有外部模型也能跑通 Demo。

具体要求：
请实现 Model Router 最小版。定义 ModelAdapter 协议，先写 RuleBasedAdapter，不调用外部 API。它能基于文本 chunk 做简单摘要、关键词标签、待办候选、风险候选。每次调用写 model_invocations 和 audit。

验收标准：
1. ModelRouter.run(purpose, input_refs, policy) 可返回结构化输出
2. RuleBasedAdapter 支持 summary/tag/task_candidate/risk_candidate 基础输出
3. 所有调用写 model_invocations
4. 敏感/critical 数据默认不允许外部调用

必须新增或更新测试：
- pytest tests/model_router/test_rule_based.py

限制：
- 不要修改用户原始目录；
- 不要默认访问网络；
- 不要绕过 Audit；
- 不要把模型生成内容写成 Evidence；
- 不要实现本 Issue 以外的大量功能。
```


## EDC-012｜OllamaAdapter 可选本地模型适配

```text
任务：EDC-012｜OllamaAdapter 可选本地模型适配

背景：
Ego Data Core v0.1 是本地优先、证据优先的个人数据操作系统。请只实现本 Issue，不扩展到无关功能。

模块：model_router
依赖：EDC-011

任务说明：
实现可选 Ollama 本地模型适配器，支持本地模型增强，但系统不能依赖它才能运行。

具体要求：
请实现 OllamaAdapter。通过本地 HTTP 调用 Ollama generate/chat 接口，超时可配置。Ollama 不可用时不得影响主流程。所有输入必须来自 ModelRouter 传入的 input_refs，不允许自行读取 Vault 全量数据。

验收标准：
1. Ollama 不存在时系统正常降级 RuleBasedAdapter
2. 支持超时、错误记录、原始输出保存
3. Prompt 不包含超出输入 refs 的数据
4. 模型输出解析失败时保存原文并标记 error

必须新增或更新测试：
- pytest tests/model_router/test_ollama_adapter.py

限制：
- 不要修改用户原始目录；
- 不要默认访问网络；
- 不要绕过 Audit；
- 不要把模型生成内容写成 Evidence；
- 不要实现本 Issue 以外的大量功能。
```


## EDC-013｜Enhancement Pipeline：summary/tag

```text
任务：EDC-013｜Enhancement Pipeline：summary/tag

背景：
Ego Data Core v0.1 是本地优先、证据优先的个人数据操作系统。请只实现本 Issue，不扩展到无关功能。

模块：twin
依赖：EDC-008, EDC-010, EDC-011

任务说明：
对 Evidence 生成摘要和标签，写 enhancements 与 evidence 链接。

具体要求：
请实现 Enhancement Pipeline 最小版。支持 enhancement_type=summary/tag。API 创建 job，worker 读取 evidence_text_chunks，调用 ModelRouter，写 enhancements 与 enhancement_evidence_links。必须保持 evidence-first，可追溯。

验收标准：
1. POST /twin/enhance 创建 job
2. worker 执行后写 enhancements
3. 每个 enhancement 必须链接至少一个 evidence
4. 记录 model_invocation_id、prompt_hash、confidence、status
5. 可查询 evidence 的 enhancement 列表

必须新增或更新测试：
- pytest tests/twin/test_enhance_summary_tag.py

限制：
- 不要修改用户原始目录；
- 不要默认访问网络；
- 不要绕过 Audit；
- 不要把模型生成内容写成 Evidence；
- 不要实现本 Issue 以外的大量功能。
```


## EDC-014｜Project Discovery v0

```text
任务：EDC-014｜Project Discovery v0

背景：
Ego Data Core v0.1 是本地优先、证据优先的个人数据操作系统。请只实现本 Issue，不扩展到无关功能。

模块：workgraph
依赖：EDC-013

任务说明：
基于目录、文件名、标签和摘要生成项目候选，允许用户确认/驳回。

具体要求：
请实现 Project Discovery v0。使用规则优先：目录名、文件名前缀、标签相似度、日期聚类。生成项目候选并链接 evidence。提供用户反馈接口 confirm/reject/edit。不要把模型推断当事实，所有项目关系标记 confidence。

验收标准：
1. 能生成 project candidates 并写 projects 表或候选状态
2. 能把 evidence 链接到 project
3. 用户可 confirm/reject/edit
4. 被驳回项目不应反复出现，除非 force_regenerate

必须新增或更新测试：
- pytest tests/workgraph/test_project_discovery.py

限制：
- 不要修改用户原始目录；
- 不要默认访问网络；
- 不要绕过 Audit；
- 不要把模型生成内容写成 Evidence；
- 不要实现本 Issue 以外的大量功能。
```


## EDC-015｜Task / Question / Risk 提取 v0

```text
任务：EDC-015｜Task / Question / Risk 提取 v0

背景：
Ego Data Core v0.1 是本地优先、证据优先的个人数据操作系统。请只实现本 Issue，不扩展到无关功能。

模块：workgraph
依赖：EDC-013, EDC-014

任务说明：
从增强数据和文本块中提取待办、未决问题、风险项，全部保持证据链接。

具体要求：
请实现 Task/Question/Risk 提取 v0。先用规则和 RuleBasedAdapter，从文本中发现“需要/待/风险/问题/不确定/下一步”等线索。写入对应表，并建立 evidence_links。输出必须带 confidence 和 proposed 状态。

验收标准：
1. 能生成 tasks/questions/risks
2. 每个对象至少关联一个 evidence
3. 状态默认为 proposed，用户确认后变 confirmed
4. 支持 feedback：confirm/reject/edit/later/convert_to_task

必须新增或更新测试：
- pytest tests/workgraph/test_extractors.py

限制：
- 不要修改用户原始目录；
- 不要默认访问网络；
- 不要绕过 Audit；
- 不要把模型生成内容写成 Evidence；
- 不要实现本 Issue 以外的大量功能。
```


## EDC-016｜Automation Opportunity 发现 v0

```text
任务：EDC-016｜Automation Opportunity 发现 v0

背景：
Ego Data Core v0.1 是本地优先、证据优先的个人数据操作系统。请只实现本 Issue，不扩展到无关功能。

模块：workgraph/operator
依赖：EDC-015

任务说明：
基于文件变化、重复文件模式和用户反馈生成低风险自动化机会。

具体要求：
请实现自动化机会发现 v0。先发现重复文件、待整理下载目录、同项目文件分散等低风险机会。只生成 action proposal，不直接执行。所有建议都要写 evidence link、risk_level、required_authorization。

验收标准：
1. 能生成 automation_opportunities
2. 每个机会包含风险等级、建议动作、所需授权
3. 默认只生成建议，不执行
4. 移动/删除/发送/上传类建议必须标记 high risk

必须新增或更新测试：
- pytest tests/workgraph/test_automation_opportunities.py

限制：
- 不要修改用户原始目录；
- 不要默认访问网络；
- 不要绕过 Audit；
- 不要把模型生成内容写成 Evidence；
- 不要实现本 Issue 以外的大量功能。
```


## EDC-017｜Daily Brief 生成器 v0

```text
任务：EDC-017｜Daily Brief 生成器 v0

背景：
Ego Data Core v0.1 是本地优先、证据优先的个人数据操作系统。请只实现本 Issue，不扩展到无关功能。

模块：brief
依赖：EDC-013, EDC-015

任务说明：
按日期生成 Ego Daily Brief，包含新增资料、项目动态、待办、问题、风险、自动化建议。

具体要求：
请实现 Daily Brief 生成器 v0。输入 date，聚合当天新增 evidence、summary/tag、tasks/questions/risks、automation_opportunities。生成 report/report_items 并导出 Markdown。原则：没有证据就不写结论；不确定则用“可能/建议核对”。

验收标准：
1. 能按日期生成 report 和 report_items
2. 每个 report_item 必须至少有一个 evidence 或 system audit reference，纯系统项除外
3. Brief 可导出 Markdown 到 vault://briefs
4. 用户可对 item 反馈 confirm/reject/later/convert_to_task
5. 没有足够数据时生成清晰的数据健康提示，而不是编造内容

必须新增或更新测试：
- pytest tests/brief/test_daily_brief.py

限制：
- 不要修改用户原始目录；
- 不要默认访问网络；
- 不要绕过 Audit；
- 不要把模型生成内容写成 Evidence；
- 不要实现本 Issue 以外的大量功能。
```


## EDC-018｜Markdown 导出器与证据引用格式

```text
任务：EDC-018｜Markdown 导出器与证据引用格式

背景：
Ego Data Core v0.1 是本地优先、证据优先的个人数据操作系统。请只实现本 Issue，不扩展到无关功能。

模块：brief/vault
依赖：EDC-017, EDC-007

任务说明：
将 Brief、Project Brief 导出为 Markdown，并用稳定格式引用 Evidence。

具体要求：
请实现 Brief Markdown 导出。输出每日简报，要求每个条目带证据引用，如 Evidence: [ev_...] 文件名 · 时间 · 摘要。不要在 Markdown 中直接泄露用户绝对路径，可显示相对标签或标题。

验收标准：
1. 导出文件包含 title、date、summary、sections、evidence references
2. 证据引用格式统一为 [ev_xxx] title/path/time
3. 不暴露敏感绝对路径，除非本地 UI 用户主动展开
4. 导出文件写入 vault://briefs

必须新增或更新测试：
- pytest tests/brief/test_markdown_export.py

限制：
- 不要修改用户原始目录；
- 不要默认访问网络；
- 不要绕过 Audit；
- 不要把模型生成内容写成 Evidence；
- 不要实现本 Issue 以外的大量功能。
```


## EDC-019｜本地 Web UI 最小版

```text
任务：EDC-019｜本地 Web UI 最小版

背景：
Ego Data Core v0.1 是本地优先、证据优先的个人数据操作系统。请只实现本 Issue，不扩展到无关功能。

模块：ui
依赖：EDC-017, EDC-005, EDC-009

任务说明：
提供本地浏览器界面查看 Sources、Evidence、Search、Daily Brief、Audit。

具体要求：
请实现本地 Web UI 最小版。可以使用 FastAPI 静态页面 + 原生 JS，不必引入复杂前端框架。页面包含：Dashboard、Sources、Search、Brief、Audit。UI 只连接本地 API。

验收标准：
1. 打开 http://127.0.0.1:8765 可看到本地 UI
2. 可查看最新 Daily Brief
3. 可查看 Evidence 列表与搜索
4. 可查看审计日志
5. 界面明确显示 Local-first 与数据源授权状态

必须新增或更新测试：
- pytest tests/api/test_static_ui.py 或 Playwright smoke test

限制：
- 不要修改用户原始目录；
- 不要默认访问网络；
- 不要绕过 Audit；
- 不要把模型生成内容写成 Evidence；
- 不要实现本 Issue 以外的大量功能。
```


## EDC-020｜Safety Kernel：隐私等级与外部调用策略

```text
任务：EDC-020｜Safety Kernel：隐私等级与外部调用策略

背景：
Ego Data Core v0.1 是本地优先、证据优先的个人数据操作系统。请只实现本 Issue，不扩展到无关功能。

模块：safety
依赖：EDC-011, EDC-004

任务说明：
根据 public/private/sensitive/critical 决定模型调用、上下文输出和动作授权。

具体要求：
请实现 Safety Kernel 的隐私策略判断。提供 can_use_external_model、can_include_evidence_in_context、requires_authorization。严格遵守 critical/sensitive/private/public 默认策略。任何阻断写 audit。

验收标准：
1. critical 默认禁止模型读取，除非显式逐次授权
2. sensitive 默认仅本地模型/规则
3. private 默认本地，外部需策略允许
4. public 可外部处理但仍需记录
5. 策略拦截写 policy_blocked audit

必须新增或更新测试：
- pytest tests/safety/test_policy.py

限制：
- 不要修改用户原始目录；
- 不要默认访问网络；
- 不要绕过 Audit；
- 不要把模型生成内容写成 Evidence；
- 不要实现本 Issue 以外的大量功能。
```


## EDC-021｜Operator Bridge：Action Plan Dry-run

```text
任务：EDC-021｜Operator Bridge：Action Plan Dry-run

背景：
Ego Data Core v0.1 是本地优先、证据优先的个人数据操作系统。请只实现本 Issue，不扩展到无关功能。

模块：operator
依赖：EDC-016, EDC-020

任务说明：
预留物理操作执行接口，v0.1 先支持 Action Plan、授权和 dry_run，不真正操作电脑。

具体要求：
请实现 Operator Bridge dry-run。它不实际控制电脑，只生成 action_plan、required_authorization、dry_run_steps。实现 /actions/propose、/actions/{id}/authorize、/actions/{id}/execute。没有授权不得执行。

验收标准：
1. POST /actions/propose 可创建 action_plan
2. 授权前 execute 返回 requires_authorization
3. dry_run 生成步骤和风险说明
4. 高风险动作必须用户授权
5. 所有 propose/authorize/execute 写 audit

必须新增或更新测试：
- pytest tests/operator/test_action_dry_run.py

限制：
- 不要修改用户原始目录；
- 不要默认访问网络；
- 不要绕过 Audit；
- 不要把模型生成内容写成 Evidence；
- 不要实现本 Issue 以外的大量功能。
```


## EDC-022｜屏幕采集 Connector v0：手动截图入库

```text
任务：EDC-022｜屏幕采集 Connector v0：手动截图入库

背景：
Ego Data Core v0.1 是本地优先、证据优先的个人数据操作系统。请只实现本 Issue，不扩展到无关功能。

模块：connectors/screen
依赖：EDC-005, EDC-007

任务说明：
v0.1 先实现手动上传/本机截图导入，生成 screenshot evidence，为未来 HDMI 采集预留接口。

具体要求：
请实现屏幕采集 Connector v0。先支持导入已有图片文件作为 screenshot evidence；可选支持 PIL/ImageGrab 在桌面环境截图。为 HDMI 采集保留接口类，但不要实现设备驱动。

验收标准：
1. 可通过 API 或 CLI 导入 screenshot
2. 生成 raw_object/object_version/evidence，evidence_type=screenshot
3. 记录 active_window/app_name 可选 metadata
4. 不做全天候录屏

必须新增或更新测试：
- pytest tests/connectors/test_screen_capture.py

限制：
- 不要修改用户原始目录；
- 不要默认访问网络；
- 不要绕过 Audit；
- 不要把模型生成内容写成 Evidence；
- 不要实现本 Issue 以外的大量功能。
```


## EDC-023｜Screenshot OCR Enhancement v0

```text
任务：EDC-023｜Screenshot OCR Enhancement v0

背景：
Ego Data Core v0.1 是本地优先、证据优先的个人数据操作系统。请只实现本 Issue，不扩展到无关功能。

模块：twin/screen
依赖：EDC-022, EDC-013

任务说明：
对 screenshot evidence 生成 OCR 文本增强，先支持可选 OCR；OCR 不可用时生成占位 enhancement。

具体要求：
请实现 Screenshot OCR Enhancement v0。定义 OCRAdapter 接口，可先写 MockOCRAdapter 或 EasyOCR/PaddleOCR 可选适配。OCR 输出写 enhancement，包含 text 和可选 boxes。不可用时写 status=unsupported，不影响其他流程。

验收标准：
1. 支持 OCR adapter 接口
2. 没有 OCR 环境时不崩溃，写 unsupported 状态
3. OCR 输出必须链接 screenshot evidence
4. 保留坐标/区域 metadata 结构

必须新增或更新测试：
- pytest tests/twin/test_screenshot_ocr.py

限制：
- 不要修改用户原始目录；
- 不要默认访问网络；
- 不要绕过 Audit；
- 不要把模型生成内容写成 Evidence；
- 不要实现本 Issue 以外的大量功能。
```


## EDC-024｜Compute Fabric 节点注册 v0

```text
任务：EDC-024｜Compute Fabric 节点注册 v0

背景：
Ego Data Core v0.1 是本地优先、证据优先的个人数据操作系统。请只实现本 Issue，不扩展到无关功能。

模块：compute_fabric
依赖：EDC-001

任务说明：
注册本机、局域网服务器、外部模型节点的能力信息，为后续分层调度打基础。

具体要求：
请实现 Compute Fabric 节点注册 v0。可手动注册本机、本地服务器、外部 API 节点，记录 capabilities_json、trust_level、cost_profile、energy_profile。暂不实现自动发现。

验收标准：
1. 可手动注册 compute node
2. 记录 CPU/GPU/NPU/内存/模型/信任等级/能耗估算
3. Model Router 可读取节点能力
4. 外部节点默认不可处理 sensitive/critical

必须新增或更新测试：
- pytest tests/compute_fabric/test_nodes.py

限制：
- 不要修改用户原始目录；
- 不要默认访问网络；
- 不要绕过 Audit；
- 不要把模型生成内容写成 Evidence；
- 不要实现本 Issue 以外的大量功能。
```


## EDC-025｜CLI 工具：扫描、增强、生成 Brief

```text
任务：EDC-025｜CLI 工具：扫描、增强、生成 Brief

背景：
Ego Data Core v0.1 是本地优先、证据优先的个人数据操作系统。请只实现本 Issue，不扩展到无关功能。

模块：cli
依赖：EDC-006, EDC-013, EDC-017

任务说明：
提供无需 UI 的命令行入口，方便测试与演示。

具体要求：
请实现 CLI。使用 typer 或 argparse。提供 init-db、source add、scan、enhance、brief daily、audit tail。CLI 用于本地 Demo，所有命令调用同一 service 层，不绕过业务逻辑。

验收标准：
1. ego init-db
2. ego source add <path>
3. ego scan <source_id>
4. ego enhance --date YYYY-MM-DD
5. ego brief daily --date YYYY-MM-DD
6. 命令失败返回非零 exit code 并写日志

必须新增或更新测试：
- pytest tests/cli/test_cli.py

限制：
- 不要修改用户原始目录；
- 不要默认访问网络；
- 不要绕过 Audit；
- 不要把模型生成内容写成 Evidence；
- 不要实现本 Issue 以外的大量功能。
```


## EDC-026｜Demo Seed 数据与一键演示脚本

```text
任务：EDC-026｜Demo Seed 数据与一键演示脚本

背景：
Ego Data Core v0.1 是本地优先、证据优先的个人数据操作系统。请只实现本 Issue，不扩展到无关功能。

模块：demo
依赖：EDC-017, EDC-025

任务说明：
构造可公开展示的样例数据，一键跑通扫描、增强、Work Graph、Daily Brief。

具体要求：
请创建 Demo Seed 数据和一键演示脚本。构造一个 sample_workspace，包含 Ego 项目计划、会议纪要、报价草案、待办清单、重复文件。run_demo.sh 完成 init-db、add source、scan、enhance、discover、brief，最后打印 Brief Markdown 路径。

验收标准：
1. 全新环境执行 scripts/run_demo.sh 可生成 Daily Brief
2. Demo 数据不包含真实隐私
3. 输出 Brief 中每个条目都有 Evidence 引用
4. 5 分钟内可以演示产品核心闭环

必须新增或更新测试：
- bash scripts/run_demo.sh
- pytest tests/demo/test_demo_smoke.py

限制：
- 不要修改用户原始目录；
- 不要默认访问网络；
- 不要绕过 Audit；
- 不要把模型生成内容写成 Evidence；
- 不要实现本 Issue 以外的大量功能。
```


## EDC-027｜数据健康检查 Data Health

```text
任务：EDC-027｜数据健康检查 Data Health

背景：
Ego Data Core v0.1 是本地优先、证据优先的个人数据操作系统。请只实现本 Issue，不扩展到无关功能。

模块：brief/data_health
依赖：EDC-017

任务说明：
在 Daily Brief 中加入数据覆盖度、解析失败、未增强证据、隐私阻断等系统健康信息。

具体要求：
请实现 Data Health 汇报项。Daily Brief 中加入系统状态：新增 evidence 数、解析失败数、enhancement 完成率、policy_blocked 数、待处理 job 数、建议用户新增数据源或授权。

验收标准：
1. 显示新增文件数量、解析成功率、增强完成率
2. 显示失败 job 和可重试建议
3. 显示被隐私策略阻断的外部调用次数
4. 没有数据时给出下一步配置建议

必须新增或更新测试：
- pytest tests/brief/test_data_health.py

限制：
- 不要修改用户原始目录；
- 不要默认访问网络；
- 不要绕过 Audit；
- 不要把模型生成内容写成 Evidence；
- 不要实现本 Issue 以外的大量功能。
```


## EDC-028｜错误处理与日志规范

```text
任务：EDC-028｜错误处理与日志规范

背景：
Ego Data Core v0.1 是本地优先、证据优先的个人数据操作系统。请只实现本 Issue，不扩展到无关功能。

模块：kernel/logging
依赖：EDC-000, EDC-004

任务说明：
统一异常类型、日志格式和错误响应，避免后台任务静默失败。

具体要求：
请实现统一错误处理与日志。定义 EgoError 基类和子类：PolicyBlockedError、NotFoundError、ValidationError、ConnectorError、ModelError、StorageError。API 返回稳定 JSON。日志中避免输出用户原文内容。

验收标准：
1. API 错误返回稳定 JSON：code/message/request_id
2. 后台 job 错误写 jobs.error_message 和 audit
3. 日志不输出完整敏感文本，只输出 ID/摘要
4. 有全局 FastAPI exception handler

必须新增或更新测试：
- pytest tests/kernel/test_errors.py

限制：
- 不要修改用户原始目录；
- 不要默认访问网络；
- 不要绕过 Audit；
- 不要把模型生成内容写成 Evidence；
- 不要实现本 Issue 以外的大量功能。
```


## EDC-029｜测试基座与临时工作区 Fixture

```text
任务：EDC-029｜测试基座与临时工作区 Fixture

背景：
Ego Data Core v0.1 是本地优先、证据优先的个人数据操作系统。请只实现本 Issue，不扩展到无关功能。

模块：tests
依赖：EDC-000, EDC-001

任务说明：
建立 pytest fixture：临时 EGO_DATA_HOME、内存/临时 SQLite、样例文件、测试客户端。

具体要求：
请建立 pytest 测试基座。conftest 提供 tmp_data_home、db_path、client、sample_workspace fixtures。所有测试必须使用临时目录，严禁读写真实用户目录。

验收标准：
1. 每个测试用例隔离数据目录
2. 测试不会读写用户真实目录
3. API TestClient 可复用
4. 提供 sample txt/md/docx/pdf 或可跳过 pdf/docx 依赖

必须新增或更新测试：
- pytest

限制：
- 不要修改用户原始目录；
- 不要默认访问网络；
- 不要绕过 Audit；
- 不要把模型生成内容写成 Evidence；
- 不要实现本 Issue 以外的大量功能。
```


## EDC-030｜OpenAPI 同步与契约测试

```text
任务：EDC-030｜OpenAPI 同步与契约测试

背景：
Ego Data Core v0.1 是本地优先、证据优先的个人数据操作系统。请只实现本 Issue，不扩展到无关功能。

模块：api
依赖：EDC-017, EDC-021

任务说明：
确保实现 API 与 openapi.yaml 草案一致，并生成本地 OpenAPI 文档。

具体要求：
请实现 OpenAPI 契约测试。读取现有草案，校验实现中的核心路径存在。若字段不完全一致，在 docs/api_contract.md 中列差异和原因。FastAPI 自动生成 /openapi.json。

验收标准：
1. FastAPI /openapi.json 可访问
2. 核心路径与草案一致或有差异说明
3. 契约测试覆盖 health/sources/vault/twin/briefs/actions/audit
4. README 标明 API 仍为 v0.1 local API

必须新增或更新测试：
- pytest tests/api/test_openapi_contract.py

限制：
- 不要修改用户原始目录；
- 不要默认访问网络；
- 不要绕过 Audit；
- 不要把模型生成内容写成 Evidence；
- 不要实现本 Issue 以外的大量功能。
```
