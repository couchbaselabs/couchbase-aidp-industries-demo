/* Couchbase AIDP Industries Demo — frontend.
 * Vanilla JS, no build step (same choice the reference Procurement
 * Command Center app made) — one dashboard shell re-skinned per industry
 * entirely from what the backend returns.
 */
const API_BASE = `${window.location.protocol}//${window.location.hostname}:4100/api`;

const state = {
  industries: [],
  current: null, // full industry detail
  entities: [],
  selectedEntityId: null,
  sessionId: `browser-${Math.random().toString(36).slice(2, 10)}`,
};

const el = (id) => document.getElementById(id);

async function api(path, options) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) throw new Error(`${path} -> HTTP ${res.status}`);
  return res.json();
}

function fmt(value, format) {
  if (format === "currency") return `$${Number(value).toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
  if (format === "percent") return `${value}%`;
  return value;
}

// ---------------------------------------------------------------------------
// Status badges
// ---------------------------------------------------------------------------
async function refreshBadges() {
  try {
    const health = await api("/health");
    el("cbBadge").textContent = `Couchbase: ${health.status}`;
    el("cbBadge").className = "badge " + (health.status === "ok" ? "badge-ok" : "badge-warn");
  } catch {
    el("cbBadge").textContent = "Couchbase: unreachable";
    el("cbBadge").className = "badge badge-warn";
  }
  try {
    const aom = await api("/aom/status");
    el("aomBadge").textContent = aom.reachable ? "AOM: connected" : "AOM: fallback mode";
    el("aomBadge").className = "badge " + (aom.reachable ? "badge-ok" : "badge-warn");
  } catch {
    el("aomBadge").textContent = "AOM: fallback mode";
    el("aomBadge").className = "badge badge-warn";
  }
}

// ---------------------------------------------------------------------------
// Picker view
// ---------------------------------------------------------------------------
async function loadPicker() {
  const { industries } = await api("/industries");
  state.industries = industries;
  const grid = el("industryGrid");
  grid.innerHTML = "";
  for (const ind of industries) {
    const card = document.createElement("div");
    card.className = "industry-card";
    card.style.setProperty("--card-accent", ind.color);
    card.innerHTML = `
      <div class="icon">${ind.icon}</div>
      <h3>${ind.name}</h3>
      <p>${ind.tagline}</p>
      <div class="examples">${ind.examples.join(", ")}</div>
    `;
    card.addEventListener("click", () => openIndustry(ind.id));
    grid.appendChild(card);
  }
}

function showView(view) {
  el("pickerView").hidden = view !== "picker";
  el("dashboardView").hidden = view !== "dashboard";
  el("backBtn").hidden = view !== "dashboard";
}

// ---------------------------------------------------------------------------
// Dashboard view
// ---------------------------------------------------------------------------
async function openIndustry(industryId) {
  const detail = await api(`/industries/${industryId}`);
  state.current = detail;
  document.documentElement.style.setProperty("--accent", detail.color);

  el("dIcon").textContent = detail.icon;
  el("dName").textContent = detail.name;
  el("dTagline").textContent = detail.tagline;

  renderKpis(detail.kpis);
  renderRoadmap(detail.roadmap);
  renderCopilotActions(detail.copilot_actions);
  el("copilotMessages").innerHTML = "";

  const { entities } = await api(`/industries/${industryId}/entities`);
  state.entities = entities;
  state.selectedEntityId = null;
  renderEntityList();
  el("entityDetail").innerHTML = '<p class="empty-hint">Select a row from the list to see agent recommendations.</p>';

  await refreshAccuracy();
  await refreshDemoStatus();
  showView("dashboard");
  switchTab("feed");
}

function renderKpis(kpis) {
  const row = el("kpiRow");
  row.innerHTML = "";
  for (const k of kpis) {
    const card = document.createElement("div");
    card.className = "kpi-card";
    card.innerHTML = `<div class="value">${fmt(k.value, k.format)}</div><div class="label">${k.label}</div>`;
    row.appendChild(card);
  }
}

function renderRoadmap(roadmap) {
  const list = el("roadmapList");
  list.innerHTML = "";
  for (const item of roadmap) {
    const li = document.createElement("li");
    li.textContent = item;
    list.appendChild(li);
  }
}

function renderEntityList() {
  const list = el("entityList");
  list.innerHTML = "";
  const titleField = state.current.entity_title_field;
  const subtitleField = state.current.entity_subtitle_field;
  for (const entity of state.entities) {
    const row = document.createElement("div");
    row.className = "entity-row" + (entity.id === state.selectedEntityId ? " selected" : "");
    row.innerHTML = `<div class="title">${entity[titleField]}</div><div class="subtitle">${entity[subtitleField] ?? ""}</div>`;
    row.addEventListener("click", () => selectEntity(entity.id));
    list.appendChild(row);
  }
}

async function selectEntity(entityId) {
  state.selectedEntityId = entityId;
  renderEntityList();
  const detailEl = el("entityDetail");
  detailEl.innerHTML = '<p class="empty-hint">Computing agent decisions…</p>';
  try {
    const result = await api(`/industries/${state.current.id}/entities/${entityId}/decision?session_id=${state.sessionId}`);
    renderEntityDetail(entityId, result);
  } catch (err) {
    detailEl.innerHTML = `<p class="empty-hint">Failed to load decision: ${err.message}</p>`;
  }
}

function renderEntityDetail(entityId, result) {
  const detailEl = el("entityDetail");
  const cache = result.cache;
  const cacheBadge = `<span class="cache-badge ${cache.status === "hit" ? "cache-hit" : "cache-miss"}">${cache.status === "hit" ? "⚡ cache hit" : "↻ live"} (${cache.latency_ms}ms)</span>`;

  let html = `<h3>${entityId} ${cacheBadge}</h3>`;
  for (const agent of result.decision.agents) {
    const sourceTag = agent.rationale_source === "aom" ? "via AOM" : "rule-based fallback";
    html += `
      <div class="agent-card">
        <h4><span class="severity-dot sev-${agent.severity}"></span>${agent.agent_name}<span class="source-tag">${sourceTag}</span></h4>
        <div><strong>${agent.recommendation}</strong></div>
        <div class="rationale">${agent.rationale}</div>
        <div class="impact">${agent.impact_label}: ${agent.impact_value} · confidence ${Math.round(agent.confidence * 100)}%</div>
        <div class="action-row">
          <button class="accept" data-agent="${agent.agent_id}" data-action="accept">Accept</button>
          <button class="reject" data-agent="${agent.agent_id}" data-action="reject">Reject</button>
        </div>
      </div>
    `;
  }
  detailEl.innerHTML = html;
  detailEl.querySelectorAll(".action-row button").forEach((btn) => {
    btn.addEventListener("click", async () => {
      await api(`/industries/${state.current.id}/entities/${entityId}/action`, {
        method: "POST",
        body: JSON.stringify({ agent_id: btn.dataset.agent, action: btn.dataset.action }),
      });
      btn.parentElement.querySelectorAll("button").forEach((b) => (b.disabled = true));
      btn.textContent = btn.dataset.action === "accept" ? "Accepted ✓" : "Rejected ✕";
      refreshAccuracy();
    });
  });
}

// ---------------------------------------------------------------------------
// Copilot tab
// ---------------------------------------------------------------------------
function renderCopilotActions(actions) {
  const container = el("copilotActions");
  container.innerHTML = "";
  for (const action of actions) {
    const btn = document.createElement("button");
    btn.textContent = action.label;
    btn.addEventListener("click", () => sendCopilot({ action_id: action.id }));
    container.appendChild(btn);
  }
}

function appendMessage(role, text) {
  const messages = el("copilotMessages");
  const div = document.createElement("div");
  div.className = `msg ${role}`;
  div.textContent = text;
  messages.appendChild(div);
  messages.scrollTop = messages.scrollHeight;
}

async function sendCopilot({ action_id, message }) {
  appendMessage("user", message || `(quick action) ${action_id}`);
  try {
    const reply = await api(`/industries/${state.current.id}/copilot/chat`, {
      method: "POST",
      body: JSON.stringify({ action_id, message, entity_id: state.selectedEntityId, session_id: state.sessionId }),
    });
    appendMessage("bot", `${reply.reply}${reply.source === "fallback" ? "  [rule-based fallback]" : ""}`);
  } catch (err) {
    appendMessage("bot", `Sorry, that failed: ${err.message}`);
  }
}

// ---------------------------------------------------------------------------
// Architecture / accuracy / demo tab
// ---------------------------------------------------------------------------
async function refreshAccuracy() {
  const { agents } = await api(`/industries/${state.current.id}/accuracy`);
  const container = el("accuracyTable");
  if (!agents.length) {
    container.innerHTML = '<p class="empty-hint">No accept/reject actions recorded yet this session.</p>';
    return;
  }
  let html = '<table class="acc-table"><tr><th>Agent</th><th>Accept</th><th>Reject</th><th>Accuracy</th></tr>';
  for (const a of agents) {
    html += `<tr><td>${a.agent_id}</td><td>${a.accept}</td><td>${a.reject}</td><td>${a.accuracy_pct ?? "—"}%</td></tr>`;
  }
  html += "</table>";
  container.innerHTML = html;
}

async function refreshDemoStatus() {
  const status = await api("/demo/status");
  renderDemoStatus(status);
}

function renderDemoStatus(status) {
  const running = status.running && status.industry_id === state.current.id;
  el("demoStartBtn").disabled = running;
  el("demoStopBtn").disabled = !running;
  if (running) {
    el("demoStatus").textContent = `Running with ${el("demoOperators").value} simulated operators · ${status.total_calls} calls · trailing 60s hit rate: ${status.trailing_60s_hit_rate_pct ?? "warming up"}%`;
  } else if (status.running) {
    el("demoStatus").textContent = `Running for a different industry (${status.industry_id}). Stop it first.`;
  } else {
    el("demoStatus").textContent = "Not running.";
  }
}

// ---------------------------------------------------------------------------
// Tabs
// ---------------------------------------------------------------------------
function switchTab(tab) {
  document.querySelectorAll(".tab-btn").forEach((b) => b.classList.toggle("active", b.dataset.tab === tab));
  el("tab-feed").hidden = tab !== "feed";
  el("tab-copilot").hidden = tab !== "copilot";
  el("tab-architecture").hidden = tab !== "architecture";
}

// ---------------------------------------------------------------------------
// Wiring
// ---------------------------------------------------------------------------
document.querySelectorAll(".tab-btn").forEach((btn) => btn.addEventListener("click", () => switchTab(btn.dataset.tab)));
el("backBtn").addEventListener("click", () => showView("picker"));
el("copilotForm").addEventListener("submit", (e) => {
  e.preventDefault();
  const input = el("copilotInput");
  const message = input.value.trim();
  if (!message) return;
  input.value = "";
  sendCopilot({ message });
});
el("demoStartBtn").addEventListener("click", async () => {
  const operators = parseInt(el("demoOperators").value, 10) || 25;
  const status = await api("/demo/start", { method: "POST", body: JSON.stringify({ industry_id: state.current.id, operators }) });
  renderDemoStatus(status);
});
el("demoStopBtn").addEventListener("click", async () => {
  const status = await api("/demo/stop", { method: "POST" });
  renderDemoStatus(status);
});

setInterval(() => {
  if (state.current && !el("tab-architecture").hidden) refreshDemoStatus();
}, 3000);
setInterval(refreshBadges, 15000);

showView("picker");
refreshBadges();
loadPicker().catch((err) => {
  el("industryGrid").innerHTML = `<p>Could not reach the backend at ${API_BASE}: ${err.message}. Is it running?</p>`;
});
