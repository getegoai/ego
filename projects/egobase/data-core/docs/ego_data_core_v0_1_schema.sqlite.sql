-- Ego Data Core v0.1 SQLite Schema
-- Version: 0.1
-- Date: 2026-05-28
-- Notes:
--   1. SQLite-first for local deployment.
--   2. JSON fields are stored as TEXT; application layer validates JSON.
--   3. Large binary objects are stored in filesystem vault, not in DB.
--   4. Foreign keys should be enabled: PRAGMA foreign_keys = ON;

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
  user_id TEXT PRIMARY KEY,
  display_name TEXT NOT NULL,
  timezone TEXT NOT NULL DEFAULT 'Asia/Shanghai',
  locale TEXT NOT NULL DEFAULT 'zh-CN',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS devices (
  device_id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  device_type TEXT NOT NULL CHECK (device_type IN ('pc','ego_node','server','sensor','phone','unknown')),
  name TEXT NOT NULL,
  hostname TEXT,
  os TEXT,
  capabilities_json TEXT NOT NULL DEFAULT '{}',
  trust_level TEXT NOT NULL DEFAULT 'local' CHECK (trust_level IN ('local','trusted_lan','external')),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS sources (
  source_id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  device_id TEXT,
  source_type TEXT NOT NULL CHECK (source_type IN ('filesystem','screen','browser','operator','sensor','manual','unknown')),
  name TEXT NOT NULL,
  root_uri TEXT NOT NULL,
  enabled INTEGER NOT NULL DEFAULT 1,
  privacy_level TEXT NOT NULL DEFAULT 'private' CHECK (privacy_level IN ('public','private','sensitive','critical')),
  scan_policy_json TEXT NOT NULL DEFAULT '{}',
  retention_policy_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (user_id) REFERENCES users(user_id),
  FOREIGN KEY (device_id) REFERENCES devices(device_id)
);

CREATE INDEX IF NOT EXISTS idx_sources_user_type ON sources(user_id, source_type);

CREATE TABLE IF NOT EXISTS raw_objects (
  raw_object_id TEXT PRIMARY KEY,
  source_id TEXT NOT NULL,
  object_type TEXT NOT NULL CHECK (object_type IN ('file','screenshot','web_snapshot','event','operator_log','audio','video','image','unknown')),
  original_uri TEXT NOT NULL,
  canonical_uri TEXT,
  content_hash TEXT,
  size_bytes INTEGER,
  mime_type TEXT,
  title TEXT,
  created_at TEXT NOT NULL,
  modified_at TEXT,
  captured_at TEXT,
  current_version_id TEXT,
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','missing','deleted','archived','error')),
  privacy_level TEXT NOT NULL DEFAULT 'private' CHECK (privacy_level IN ('public','private','sensitive','critical')),
  metadata_json TEXT NOT NULL DEFAULT '{}',
  FOREIGN KEY (source_id) REFERENCES sources(source_id)
);

CREATE INDEX IF NOT EXISTS idx_raw_objects_source ON raw_objects(source_id);
CREATE INDEX IF NOT EXISTS idx_raw_objects_hash ON raw_objects(content_hash);
CREATE INDEX IF NOT EXISTS idx_raw_objects_uri ON raw_objects(original_uri);
CREATE INDEX IF NOT EXISTS idx_raw_objects_captured ON raw_objects(captured_at);

CREATE TABLE IF NOT EXISTS object_versions (
  version_id TEXT PRIMARY KEY,
  raw_object_id TEXT NOT NULL,
  version_no INTEGER NOT NULL,
  storage_uri TEXT NOT NULL,
  content_hash TEXT NOT NULL,
  size_bytes INTEGER,
  extracted_text_uri TEXT,
  captured_at TEXT NOT NULL,
  metadata_json TEXT NOT NULL DEFAULT '{}',
  FOREIGN KEY (raw_object_id) REFERENCES raw_objects(raw_object_id),
  UNIQUE(raw_object_id, version_no)
);

CREATE INDEX IF NOT EXISTS idx_object_versions_object ON object_versions(raw_object_id);
CREATE INDEX IF NOT EXISTS idx_object_versions_hash ON object_versions(content_hash);

CREATE TABLE IF NOT EXISTS evidence (
  evidence_id TEXT PRIMARY KEY,
  raw_object_id TEXT NOT NULL,
  version_id TEXT,
  evidence_type TEXT NOT NULL CHECK (evidence_type IN ('document','screenshot','text_span','image_region','web_snapshot','event','operator_log','audio_segment','video_segment','unknown')),
  evidence_uri TEXT,
  evidence_selector_json TEXT NOT NULL DEFAULT '{}',
  captured_at TEXT NOT NULL,
  source_ts_start TEXT,
  source_ts_end TEXT,
  content_hash TEXT,
  privacy_level TEXT NOT NULL DEFAULT 'private' CHECK (privacy_level IN ('public','private','sensitive','critical')),
  retention_policy TEXT NOT NULL DEFAULT 'keep' CHECK (retention_policy IN ('keep','rolling','manual_review')),
  user_confirmed INTEGER NOT NULL DEFAULT 0,
  metadata_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (raw_object_id) REFERENCES raw_objects(raw_object_id),
  FOREIGN KEY (version_id) REFERENCES object_versions(version_id)
);

CREATE INDEX IF NOT EXISTS idx_evidence_object ON evidence(raw_object_id);
CREATE INDEX IF NOT EXISTS idx_evidence_version ON evidence(version_id);
CREATE INDEX IF NOT EXISTS idx_evidence_type ON evidence(evidence_type);
CREATE INDEX IF NOT EXISTS idx_evidence_captured ON evidence(captured_at);
CREATE INDEX IF NOT EXISTS idx_evidence_privacy ON evidence(privacy_level);

CREATE TABLE IF NOT EXISTS evidence_text_chunks (
  chunk_id TEXT PRIMARY KEY,
  evidence_id TEXT NOT NULL,
  chunk_index INTEGER NOT NULL,
  text TEXT NOT NULL,
  token_count INTEGER,
  language TEXT,
  page_no INTEGER,
  char_start INTEGER,
  char_end INTEGER,
  bbox_json TEXT,
  created_at TEXT NOT NULL,
  FOREIGN KEY (evidence_id) REFERENCES evidence(evidence_id),
  UNIQUE(evidence_id, chunk_index)
);

CREATE INDEX IF NOT EXISTS idx_chunks_evidence ON evidence_text_chunks(evidence_id);
CREATE INDEX IF NOT EXISTS idx_chunks_page ON evidence_text_chunks(page_no);

CREATE VIRTUAL TABLE IF NOT EXISTS evidence_text_fts USING fts5(
  chunk_id UNINDEXED,
  evidence_id UNINDEXED,
  text,
  tokenize = 'unicode61'
);

CREATE TABLE IF NOT EXISTS enhancements (
  enhancement_id TEXT PRIMARY KEY,
  enhancement_type TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','verified','rejected','superseded','error')),
  content_json TEXT NOT NULL DEFAULT '{}',
  confidence REAL,
  model_id TEXT,
  model_runtime TEXT,
  prompt_hash TEXT,
  generated_at TEXT NOT NULL,
  supersedes_id TEXT,
  verified_by_user INTEGER NOT NULL DEFAULT 0,
  privacy_level TEXT NOT NULL DEFAULT 'private' CHECK (privacy_level IN ('public','private','sensitive','critical')),
  metadata_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (supersedes_id) REFERENCES enhancements(enhancement_id)
);

CREATE INDEX IF NOT EXISTS idx_enhancements_type ON enhancements(enhancement_type);
CREATE INDEX IF NOT EXISTS idx_enhancements_status ON enhancements(status);
CREATE INDEX IF NOT EXISTS idx_enhancements_generated ON enhancements(generated_at);

CREATE TABLE IF NOT EXISTS enhancement_evidence_links (
  enhancement_id TEXT NOT NULL,
  evidence_id TEXT NOT NULL,
  weight REAL NOT NULL DEFAULT 1.0,
  trace_note TEXT,
  created_at TEXT NOT NULL,
  PRIMARY KEY (enhancement_id, evidence_id),
  FOREIGN KEY (enhancement_id) REFERENCES enhancements(enhancement_id),
  FOREIGN KEY (evidence_id) REFERENCES evidence(evidence_id)
);

CREATE TABLE IF NOT EXISTS entities (
  entity_id TEXT PRIMARY KEY,
  entity_type TEXT NOT NULL,
  canonical_name TEXT NOT NULL,
  aliases_json TEXT NOT NULL DEFAULT '[]',
  metadata_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_entities_type_name ON entities(entity_type, canonical_name);

CREATE TABLE IF NOT EXISTS entity_mentions (
  mention_id TEXT PRIMARY KEY,
  entity_id TEXT NOT NULL,
  evidence_id TEXT NOT NULL,
  enhancement_id TEXT,
  mention_text TEXT NOT NULL,
  selector_json TEXT NOT NULL DEFAULT '{}',
  confidence REAL,
  created_at TEXT NOT NULL,
  FOREIGN KEY (entity_id) REFERENCES entities(entity_id),
  FOREIGN KEY (evidence_id) REFERENCES evidence(evidence_id),
  FOREIGN KEY (enhancement_id) REFERENCES enhancements(enhancement_id)
);

CREATE TABLE IF NOT EXISTS embeddings (
  embedding_id TEXT PRIMARY KEY,
  subject_type TEXT NOT NULL CHECK (subject_type IN ('evidence','chunk','enhancement','project','task','report_item')),
  subject_id TEXT NOT NULL,
  model_id TEXT NOT NULL,
  vector_store TEXT NOT NULL,
  vector_ref TEXT NOT NULL,
  dimension INTEGER,
  created_at TEXT NOT NULL,
  metadata_json TEXT NOT NULL DEFAULT '{}',
  UNIQUE(subject_type, subject_id, model_id)
);

CREATE TABLE IF NOT EXISTS projects (
  project_id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','paused','completed','archived')),
  summary TEXT,
  confidence REAL,
  user_confirmed INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);

CREATE TABLE IF NOT EXISTS project_links (
  project_id TEXT NOT NULL,
  subject_type TEXT NOT NULL CHECK (subject_type IN ('raw_object','evidence','enhancement','task','question','risk','automation','report')),
  subject_id TEXT NOT NULL,
  relation_type TEXT NOT NULL DEFAULT 'related_to',
  confidence REAL,
  user_confirmed INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  PRIMARY KEY (project_id, subject_type, subject_id, relation_type),
  FOREIGN KEY (project_id) REFERENCES projects(project_id)
);

CREATE TABLE IF NOT EXISTS tasks (
  task_id TEXT PRIMARY KEY,
  project_id TEXT,
  title TEXT NOT NULL,
  description TEXT,
  status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','in_progress','done','cancelled','deferred')),
  priority TEXT NOT NULL DEFAULT 'medium' CHECK (priority IN ('low','medium','high','critical')),
  due_date TEXT,
  source_enhancement_id TEXT,
  confidence REAL,
  user_confirmed INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  metadata_json TEXT NOT NULL DEFAULT '{}',
  FOREIGN KEY (project_id) REFERENCES projects(project_id),
  FOREIGN KEY (source_enhancement_id) REFERENCES enhancements(enhancement_id)
);

CREATE INDEX IF NOT EXISTS idx_tasks_project_status ON tasks(project_id, status);

CREATE TABLE IF NOT EXISTS questions (
  question_id TEXT PRIMARY KEY,
  project_id TEXT,
  title TEXT NOT NULL,
  body TEXT,
  status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','answered','dismissed','deferred')),
  importance TEXT NOT NULL DEFAULT 'medium' CHECK (importance IN ('low','medium','high','critical')),
  source_enhancement_id TEXT,
  confidence REAL,
  user_confirmed INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  metadata_json TEXT NOT NULL DEFAULT '{}',
  FOREIGN KEY (project_id) REFERENCES projects(project_id),
  FOREIGN KEY (source_enhancement_id) REFERENCES enhancements(enhancement_id)
);

CREATE TABLE IF NOT EXISTS risks (
  risk_id TEXT PRIMARY KEY,
  project_id TEXT,
  title TEXT NOT NULL,
  description TEXT,
  risk_level TEXT NOT NULL DEFAULT 'medium' CHECK (risk_level IN ('low','medium','high','critical')),
  status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','mitigated','accepted','dismissed')),
  mitigation TEXT,
  source_enhancement_id TEXT,
  confidence REAL,
  user_confirmed INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  metadata_json TEXT NOT NULL DEFAULT '{}',
  FOREIGN KEY (project_id) REFERENCES projects(project_id),
  FOREIGN KEY (source_enhancement_id) REFERENCES enhancements(enhancement_id)
);

CREATE TABLE IF NOT EXISTS automations (
  automation_id TEXT PRIMARY KEY,
  project_id TEXT,
  title TEXT NOT NULL,
  description TEXT,
  pattern_json TEXT NOT NULL DEFAULT '{}',
  risk_level TEXT NOT NULL DEFAULT 'low' CHECK (risk_level IN ('low','medium','high','critical')),
  status TEXT NOT NULL DEFAULT 'proposed' CHECK (status IN ('proposed','authorized','active','disabled','rejected')),
  requires_authorization INTEGER NOT NULL DEFAULT 1,
  source_enhancement_id TEXT,
  confidence REAL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  metadata_json TEXT NOT NULL DEFAULT '{}',
  FOREIGN KEY (project_id) REFERENCES projects(project_id),
  FOREIGN KEY (source_enhancement_id) REFERENCES enhancements(enhancement_id)
);

CREATE TABLE IF NOT EXISTS graph_edges (
  edge_id TEXT PRIMARY KEY,
  src_type TEXT NOT NULL,
  src_id TEXT NOT NULL,
  dst_type TEXT NOT NULL,
  dst_id TEXT NOT NULL,
  relation_type TEXT NOT NULL,
  confidence REAL,
  evidence_id TEXT,
  created_at TEXT NOT NULL,
  metadata_json TEXT NOT NULL DEFAULT '{}',
  FOREIGN KEY (evidence_id) REFERENCES evidence(evidence_id)
);

CREATE INDEX IF NOT EXISTS idx_graph_edges_src ON graph_edges(src_type, src_id);
CREATE INDEX IF NOT EXISTS idx_graph_edges_dst ON graph_edges(dst_type, dst_id);

CREATE TABLE IF NOT EXISTS reports (
  report_id TEXT PRIMARY KEY,
  report_type TEXT NOT NULL CHECK (report_type IN ('daily','weekly','project','data_health','automation')),
  title TEXT NOT NULL,
  report_date TEXT,
  status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','published','archived','error')),
  summary TEXT,
  generated_at TEXT NOT NULL,
  model_id TEXT,
  metadata_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_reports_type_date ON reports(report_type, report_date);

CREATE TABLE IF NOT EXISTS report_items (
  report_item_id TEXT PRIMARY KEY,
  report_id TEXT NOT NULL,
  item_order INTEGER NOT NULL,
  item_type TEXT NOT NULL CHECK (item_type IN ('project_update','new_evidence','task','question','risk','automation','decision','data_health','system')),
  title TEXT NOT NULL,
  body TEXT,
  severity TEXT NOT NULL DEFAULT 'info' CHECK (severity IN ('info','low','medium','high','critical')),
  confidence REAL,
  inferred INTEGER NOT NULL DEFAULT 0,
  user_feedback TEXT CHECK (user_feedback IN ('confirm','reject','edit','later','convert_to_task','authorize_action') OR user_feedback IS NULL),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  metadata_json TEXT NOT NULL DEFAULT '{}',
  FOREIGN KEY (report_id) REFERENCES reports(report_id)
);

CREATE INDEX IF NOT EXISTS idx_report_items_report ON report_items(report_id, item_order);

CREATE TABLE IF NOT EXISTS report_item_evidence_links (
  report_item_id TEXT NOT NULL,
  evidence_id TEXT NOT NULL,
  note TEXT,
  created_at TEXT NOT NULL,
  PRIMARY KEY (report_item_id, evidence_id),
  FOREIGN KEY (report_item_id) REFERENCES report_items(report_item_id),
  FOREIGN KEY (evidence_id) REFERENCES evidence(evidence_id)
);

CREATE TABLE IF NOT EXISTS jobs (
  job_id TEXT PRIMARY KEY,
  job_type TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','running','succeeded','failed','cancelled','blocked')),
  priority INTEGER NOT NULL DEFAULT 2,
  input_json TEXT NOT NULL DEFAULT '{}',
  output_json TEXT NOT NULL DEFAULT '{}',
  policy_json TEXT NOT NULL DEFAULT '{}',
  error_message TEXT,
  retry_count INTEGER NOT NULL DEFAULT 0,
  max_retries INTEGER NOT NULL DEFAULT 3,
  scheduled_at TEXT,
  started_at TEXT,
  finished_at TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_jobs_status_priority ON jobs(status, priority, scheduled_at);
CREATE INDEX IF NOT EXISTS idx_jobs_type ON jobs(job_type);

CREATE TABLE IF NOT EXISTS job_dependencies (
  job_id TEXT NOT NULL,
  depends_on_job_id TEXT NOT NULL,
  created_at TEXT NOT NULL,
  PRIMARY KEY (job_id, depends_on_job_id),
  FOREIGN KEY (job_id) REFERENCES jobs(job_id),
  FOREIGN KEY (depends_on_job_id) REFERENCES jobs(job_id)
);

CREATE TABLE IF NOT EXISTS model_providers (
  provider_id TEXT PRIMARY KEY,
  provider_type TEXT NOT NULL CHECK (provider_type IN ('ollama','llama_cpp','vllm','rknn','external_openai_compatible','rule')),
  name TEXT NOT NULL,
  base_url TEXT,
  enabled INTEGER NOT NULL DEFAULT 1,
  privacy_allowed_json TEXT NOT NULL DEFAULT '["public","private"]',
  config_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS models (
  model_id TEXT PRIMARY KEY,
  provider_id TEXT,
  name TEXT NOT NULL,
  model_type TEXT NOT NULL CHECK (model_type IN ('llm','vlm','embedding','ocr','reranker','classifier','rule')),
  runtime TEXT NOT NULL,
  context_window INTEGER,
  capabilities_json TEXT NOT NULL DEFAULT '{}',
  cost_profile_json TEXT NOT NULL DEFAULT '{}',
  enabled INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (provider_id) REFERENCES model_providers(provider_id)
);

CREATE TABLE IF NOT EXISTS model_invocations (
  invocation_id TEXT PRIMARY KEY,
  model_id TEXT,
  job_id TEXT,
  purpose TEXT NOT NULL,
  input_ref_uri TEXT,
  output_ref_uri TEXT,
  prompt_hash TEXT,
  input_tokens INTEGER,
  output_tokens INTEGER,
  cost_estimate REAL,
  latency_ms INTEGER,
  privacy_level TEXT NOT NULL DEFAULT 'private' CHECK (privacy_level IN ('public','private','sensitive','critical')),
  external_call INTEGER NOT NULL DEFAULT 0,
  allowed_by_policy INTEGER NOT NULL DEFAULT 1,
  status TEXT NOT NULL DEFAULT 'succeeded' CHECK (status IN ('succeeded','failed','blocked')),
  error_message TEXT,
  created_at TEXT NOT NULL,
  metadata_json TEXT NOT NULL DEFAULT '{}',
  FOREIGN KEY (model_id) REFERENCES models(model_id),
  FOREIGN KEY (job_id) REFERENCES jobs(job_id)
);

CREATE INDEX IF NOT EXISTS idx_model_invocations_model ON model_invocations(model_id);
CREATE INDEX IF NOT EXISTS idx_model_invocations_job ON model_invocations(job_id);
CREATE INDEX IF NOT EXISTS idx_model_invocations_created ON model_invocations(created_at);

CREATE TABLE IF NOT EXISTS compute_nodes (
  compute_node_id TEXT PRIMARY KEY,
  node_type TEXT NOT NULL CHECK (node_type IN ('local_pc','ego_node','lan_server','external_api','future_dock')),
  name TEXT NOT NULL,
  endpoint_uri TEXT,
  trust_level TEXT NOT NULL DEFAULT 'local' CHECK (trust_level IN ('local','trusted_lan','external')),
  capabilities_json TEXT NOT NULL DEFAULT '{}',
  energy_meter_available INTEGER NOT NULL DEFAULT 0,
  enabled INTEGER NOT NULL DEFAULT 1,
  last_seen_at TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS compute_runs (
  compute_run_id TEXT PRIMARY KEY,
  compute_node_id TEXT,
  job_id TEXT,
  invocation_id TEXT,
  status TEXT NOT NULL DEFAULT 'succeeded' CHECK (status IN ('succeeded','failed','cancelled')),
  started_at TEXT,
  finished_at TEXT,
  duration_ms INTEGER,
  energy_wh REAL,
  cost_estimate REAL,
  metadata_json TEXT NOT NULL DEFAULT '{}',
  FOREIGN KEY (compute_node_id) REFERENCES compute_nodes(compute_node_id),
  FOREIGN KEY (job_id) REFERENCES jobs(job_id),
  FOREIGN KEY (invocation_id) REFERENCES model_invocations(invocation_id)
);

CREATE TABLE IF NOT EXISTS actions (
  action_id TEXT PRIMARY KEY,
  project_id TEXT,
  title TEXT NOT NULL,
  goal TEXT,
  risk_level TEXT NOT NULL DEFAULT 'medium' CHECK (risk_level IN ('low','medium','high','critical')),
  status TEXT NOT NULL DEFAULT 'proposed' CHECK (status IN ('proposed','authorized','running','succeeded','failed','cancelled','rejected')),
  requires_authorization INTEGER NOT NULL DEFAULT 1,
  plan_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  metadata_json TEXT NOT NULL DEFAULT '{}',
  FOREIGN KEY (project_id) REFERENCES projects(project_id)
);

CREATE TABLE IF NOT EXISTS authorizations (
  authorization_id TEXT PRIMARY KEY,
  action_id TEXT,
  user_id TEXT NOT NULL,
  authorization_type TEXT NOT NULL CHECK (authorization_type IN ('one_time','session','policy')),
  scope_json TEXT NOT NULL DEFAULT '{}',
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','revoked','expired','used')),
  granted_at TEXT NOT NULL,
  expires_at TEXT,
  revoked_at TEXT,
  FOREIGN KEY (action_id) REFERENCES actions(action_id),
  FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS action_steps (
  action_step_id TEXT PRIMARY KEY,
  action_id TEXT NOT NULL,
  step_order INTEGER NOT NULL,
  step_type TEXT NOT NULL,
  description TEXT,
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','running','succeeded','failed','skipped')),
  input_json TEXT NOT NULL DEFAULT '{}',
  output_json TEXT NOT NULL DEFAULT '{}',
  pre_evidence_id TEXT,
  post_evidence_id TEXT,
  started_at TEXT,
  finished_at TEXT,
  error_message TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (action_id) REFERENCES actions(action_id),
  FOREIGN KEY (pre_evidence_id) REFERENCES evidence(evidence_id),
  FOREIGN KEY (post_evidence_id) REFERENCES evidence(evidence_id),
  UNIQUE(action_id, step_order)
);

CREATE TABLE IF NOT EXISTS policies (
  policy_id TEXT PRIMARY KEY,
  policy_type TEXT NOT NULL,
  name TEXT NOT NULL,
  enabled INTEGER NOT NULL DEFAULT 1,
  policy_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS privacy_overrides (
  override_id TEXT PRIMARY KEY,
  subject_type TEXT NOT NULL CHECK (subject_type IN ('source','raw_object','evidence','project')),
  subject_id TEXT NOT NULL,
  privacy_level TEXT NOT NULL CHECK (privacy_level IN ('public','private','sensitive','critical')),
  reason TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_logs (
  audit_id TEXT PRIMARY KEY,
  event_type TEXT NOT NULL,
  actor_type TEXT NOT NULL DEFAULT 'system' CHECK (actor_type IN ('user','system','model','operator')),
  actor_id TEXT,
  subject_type TEXT,
  subject_id TEXT,
  event_time TEXT NOT NULL,
  ip_or_device TEXT,
  detail_json TEXT NOT NULL DEFAULT '{}',
  prev_hash TEXT,
  event_hash TEXT
);

CREATE INDEX IF NOT EXISTS idx_audit_event_time ON audit_logs(event_time);
CREATE INDEX IF NOT EXISTS idx_audit_event_type ON audit_logs(event_type);
CREATE INDEX IF NOT EXISTS idx_audit_subject ON audit_logs(subject_type, subject_id);
