const shell = document.querySelector(".app-shell");
const API_BASE = shell?.dataset.apiBase || "/api/v1";

const state = {
  health: null,
  sources: { items: [], total: 0 },
  brief: null,
  audit: { items: [], total: 0 },
};

const views = {
  dashboard: "Dashboard",
  sources: "Sources",
  search: "Search",
  brief: "Brief",
  audit: "Audit",
};

document.addEventListener("DOMContentLoaded", () => {
  bindNavigation();
  bindActions();
  refreshAll();
});

function bindNavigation() {
  document.querySelectorAll(".nav-tab").forEach((button) => {
    button.addEventListener("click", () => setView(button.dataset.view));
  });
}

function bindActions() {
  byId("refresh-all")?.addEventListener("click", refreshAll);
  byId("refresh-brief")?.addEventListener("click", loadBrief);
  byId("refresh-audit")?.addEventListener("click", loadAudit);
  byId("generate-brief")?.addEventListener("click", generateBrief);
  byId("search-form")?.addEventListener("submit", (event) => {
    event.preventDefault();
    runSearch();
  });
}

function setView(name) {
  Object.keys(views).forEach((view) => {
    byId(`${view}-view`)?.classList.toggle("is-active", view === name);
  });
  document.querySelectorAll(".nav-tab").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.view === name);
  });
  byId("view-title").textContent = views[name] || "Dashboard";
}

async function refreshAll() {
  clearError();
  await Promise.allSettled([loadHealth(), loadSources(), loadBrief(), loadAudit()]);
  renderDashboard();
}

async function loadHealth() {
  try {
    state.health = await api("/health");
    const pill = byId("api-status");
    pill.textContent = state.health.status === "ok" ? "API Online" : "API Error";
    pill.className = `status-pill ${state.health.status === "ok" ? "ok" : "error"}`;
  } catch (error) {
    byId("api-status").textContent = "API Error";
    byId("api-status").className = "status-pill error";
    showError(error);
  }
}

async function loadSources() {
  try {
    state.sources = await api("/sources");
    renderSources();
    renderSourceOptions();
    renderDashboard();
  } catch (error) {
    showError(error);
  }
}

async function loadBrief() {
  try {
    state.brief = await api("/briefs/daily/latest");
    renderBrief();
    renderDashboard();
  } catch (error) {
    showError(error);
  }
}

async function generateBrief() {
  try {
    state.brief = await api("/briefs/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ report_type: "daily" }),
    });
    renderBrief();
    renderDashboard();
  } catch (error) {
    showError(error);
  }
}

async function loadAudit() {
  try {
    state.audit = await api("/audit/logs?limit=50&offset=0");
    renderAudit();
    renderDashboard();
  } catch (error) {
    showError(error);
  }
}

async function runSearch() {
  const query = byId("search-query").value.trim();
  if (!query) {
    byId("search-results").innerHTML = emptyState("Enter a query.");
    byId("search-meta").textContent = "Ready";
    return;
  }

  const params = new URLSearchParams({ q: query });
  addParam(params, "source_id", byId("search-source").value);
  addParam(params, "date_from", byId("search-from").value);
  addParam(params, "date_to", byId("search-to").value);

  byId("search-meta").textContent = "Searching";
  try {
    const payload = await api(`/search?${params.toString()}`);
    renderSearchResults(payload);
  } catch (error) {
    byId("search-meta").textContent = "Search failed";
    showError(error);
  }
}

function renderDashboard() {
  const health = state.health || {};
  const database = health.database || {};
  const sources = state.sources || { items: [], total: 0 };
  const brief = state.brief;
  const audit = state.audit || { total: 0 };
  const enabledCount = sources.items.filter((source) => source.enabled).length;

  byId("dashboard-metrics").innerHTML = [
    metric("API", health.status || "unknown", `version ${health.version || "n/a"}`),
    metric("Database", database.status || "unknown", `${database.table_count || 0} tables`),
    metric("Sources", sources.total || 0, `${enabledCount} authorized`),
    metric("Audit", audit.total || 0, "recent events"),
  ].join("");

  byId("source-summary").textContent = `${enabledCount} authorized of ${sources.total || 0}`;
  byId("source-health").innerHTML = sources.items.length
    ? sources.items.slice(0, 5).map(renderCompactSource).join("")
    : emptyState("No sources registered.");

  byId("dashboard-brief").innerHTML = brief
    ? `<div class="row-title">${escapeHtml(brief.title)}</div>
       <div class="row-meta">${escapeHtml(brief.report_date)} · ${escapeHtml(brief.status)}</div>
       <div class="brief-body">${escapeHtml(brief.summary || "")}</div>`
    : emptyState("No daily brief yet.");
}

function renderSources() {
  const sources = state.sources || { items: [], total: 0 };
  byId("sources-count").textContent = `${sources.total || 0} sources`;
  byId("sources-table").innerHTML = sources.items.length
    ? sources.items.map(renderSourceRow).join("")
    : `<tr><td colspan="6">${emptyState("No sources registered.")}</td></tr>`;
}

function renderSourceOptions() {
  const select = byId("search-source");
  const current = select.value;
  select.innerHTML = `<option value="">All sources</option>${state.sources.items
    .map((source) => `<option value="${escapeAttr(source.source_id)}">${escapeHtml(source.name)}</option>`)
    .join("")}`;
  select.value = current;
}

function renderBrief() {
  const brief = state.brief;
  if (!brief) {
    byId("brief-detail").innerHTML = emptyState("No daily brief yet.");
    return;
  }

  const items = brief.items || [];
  byId("brief-detail").innerHTML = `
    <header>
      <div>
        <h3>${escapeHtml(brief.title)}</h3>
        <div class="row-meta">${escapeHtml(brief.report_date)} · ${escapeHtml(brief.status)}</div>
      </div>
      <span class="status-pill local">${items.length} items</span>
    </header>
    <div class="brief-body">${escapeHtml(brief.summary || "")}</div>
    <div class="brief-items">
      ${items.map(renderBriefItem).join("")}
    </div>`;
}

function renderAudit() {
  const audit = state.audit || { items: [], total: 0 };
  byId("audit-list").innerHTML = audit.items.length
    ? audit.items.map(renderAuditItem).join("")
    : emptyState("No audit events.");
}

function renderSearchResults(payload) {
  byId("search-meta").textContent = `${payload.total} results · ${payload.backend}`;
  byId("search-results").innerHTML = payload.items.length
    ? payload.items.map(renderSearchItem).join("")
    : emptyState("No evidence matched.");
}

function renderSourceRow(source) {
  return `
    <tr>
      <td>${escapeHtml(source.name)}</td>
      <td>${escapeHtml(source.source_type)}</td>
      <td>${privacyBadge(source.privacy_level)}</td>
      <td>${source.enabled ? "Authorized" : "Disabled"}</td>
      <td><code>${escapeHtml(shortId(source.source_id))}</code></td>
      <td>${escapeHtml(formatDate(source.updated_at))}</td>
    </tr>`;
}

function renderCompactSource(source) {
  return `
    <div class="compact-row">
      <div>
        <div class="row-title">${escapeHtml(source.name)}</div>
        <div class="row-meta">${escapeHtml(source.source_type)} · ${escapeHtml(shortId(source.source_id))}</div>
      </div>
      ${privacyBadge(source.privacy_level)}
    </div>`;
}

function renderBriefItem(item) {
  const evidenceCount = (item.evidence_ids || []).length;
  return `
    <div class="brief-item">
      <div class="row-title">${escapeHtml(item.title)}</div>
      <div class="row-meta">${escapeHtml(item.item_type)} · ${evidenceCount} evidence</div>
      <div class="brief-body">${escapeHtml(item.body || "")}</div>
    </div>`;
}

function renderAuditItem(item) {
  const subject = [item.subject_type, shortId(item.subject_id)].filter(Boolean).join(" · ");
  return `
    <div class="audit-item">
      <div class="audit-title">${escapeHtml(item.event_type)}</div>
      <div class="audit-meta">${escapeHtml(subject || "system")} · ${escapeHtml(formatDate(item.created_at))}</div>
    </div>`;
}

function renderSearchItem(item) {
  return `
    <article class="result-item">
      <div class="result-title">${escapeHtml(item.title || item.evidence_id)}</div>
      <div class="result-meta">
        ${escapeHtml(shortId(item.evidence_id))} · chunk ${escapeHtml(String(item.chunk_index))} · ${escapeHtml(item.match_type)}
      </div>
      <div class="result-snippet">${escapeHtml(item.snippet || "")}</div>
    </article>`;
}

function metric(label, value, note) {
  return `
    <div class="metric">
      <div class="label">${escapeHtml(label)}</div>
      <div class="value">${escapeHtml(String(value))}</div>
      <div class="note">${escapeHtml(note)}</div>
    </div>`;
}

function privacyBadge(value) {
  const normalized = String(value || "private").toLowerCase();
  return `<span class="privacy ${escapeAttr(normalized)}">${escapeHtml(normalized)}</span>`;
}

async function api(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, options);
  if (!response.ok) {
    let detail = null;
    try {
      detail = await response.json();
    } catch {
      detail = { message: response.statusText };
    }
    const error = new Error(detail.message || detail.code || "Request failed");
    error.detail = detail;
    throw error;
  }
  if (response.status === 204) {
    return null;
  }
  return response.json();
}

function addParam(params, key, value) {
  if (value) {
    params.set(key, value);
  }
}

function byId(id) {
  return document.getElementById(id);
}

function showError(error) {
  const banner = byId("error-banner");
  banner.hidden = false;
  banner.textContent = error.message || "Request failed";
}

function clearError() {
  const banner = byId("error-banner");
  banner.hidden = true;
  banner.textContent = "";
}

function emptyState(text) {
  return `<div class="empty">${escapeHtml(text)}</div>`;
}

function shortId(value) {
  if (!value) {
    return "";
  }
  return value.length > 18 ? `${value.slice(0, 10)}...${value.slice(-6)}` : value;
}

function formatDate(value) {
  if (!value) {
    return "";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function escapeAttr(value) {
  return escapeHtml(value).replaceAll(" ", "-");
}
