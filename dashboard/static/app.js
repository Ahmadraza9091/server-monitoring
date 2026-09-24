const state = { status: "active", timer: null };
const $ = (id) => document.getElementById(id);
const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" }[char]));
const formatTime = (value) => {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? escapeHtml(value) : date.toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
};
const severityClass = (value) => ["critical", "warning", "info"].includes(String(value).toLowerCase()) ? String(value).toLowerCase() : "unknown";

async function api(path) {
  const response = await fetch(path, { headers: { Accept: "application/json" }, cache: "no-store" });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.error || `Request failed (${response.status})`);
  }
  return response.json();
}

function setError(message = "") {
  $("error").textContent = message;
  $("error").hidden = !message;
}

async function loadSummary() {
  const data = await api("/api/summary");
  $("metric-active").textContent = data.active;
  $("metric-unack").textContent = data.unacknowledged;
  $("metric-assigned").textContent = data.assigned;
  $("metric-resolved").textContent = data.resolved;
  $("nav-active").textContent = data.active;
  $("nav-all").textContent = data.total;
  $("nav-resolved").textContent = data.resolved;
  $("metric-active-note").textContent = `${data.severity.critical || 0} critical`;
  $("updated-label").textContent = data.last_updated ? `Last event ${formatTime(data.last_updated)}` : "No incidents recorded";
}

async function loadIncidents() {
  const params = new URLSearchParams({ status: state.status, limit: "500" });
  const severity = $("severity").value;
  const search = $("search").value.trim();
  if (severity) params.set("severity", severity);
  if (search) params.set("q", search);
  const data = await api(`/api/incidents?${params}`);
  $("result-count").textContent = data.total;
  $("view-title").textContent = state.status === "active" ? "Active incidents" : state.status === "resolved" ? "Resolved incidents" : "All incidents";
  const list = $("incident-list");
  list.innerHTML = data.items.map((item) => {
    const severityName = severityClass(item.severity);
    const resolved = Boolean(item.resolved_at);
    return `<tr data-id="${encodeURIComponent(item.occurrence_id)}"><td><div class="incident-name"><i class="severity-dot ${severityName}"></i><div><strong>${escapeHtml(item.alert)}</strong><small>${escapeHtml(item.server)}${item.summary ? ` · ${escapeHtml(item.summary)}` : ""}</small></div></div></td><td><span class="severity-label ${severityName}">${escapeHtml(item.severity || "unknown")}</span></td><td><span class="state-label ${resolved ? "resolved" : ""}">${escapeHtml(resolved ? "Resolved" : (item.status_text || item.action || "Firing"))}</span></td><td class="owner">${escapeHtml(item.assignee_name || item.user_name || "Unassigned")}</td><td class="muted">${formatTime(item.starts_at || item.created_at)}</td><td class="muted">${formatTime(item.updated_at)}</td><td class="row-action">›</td></tr>`;
  }).join("");
  $("empty").hidden = data.items.length !== 0;
  list.querySelectorAll("tr").forEach((row) => row.addEventListener("click", () => openDetail(decodeURIComponent(row.dataset.id))));
}

async function openDetail(id) {
  try {
    const item = await api(`/api/incidents/${encodeURIComponent(id)}`);
    const alert = item.alert_data || {};
    const labels = alert.labels || {};
    const annotations = alert.annotations || {};
    $("detail-title").textContent = item.alert || labels.alertname || "Incident";
    $("detail-content").innerHTML = `<div class="detail-grid"><div class="detail-field"><label>Severity</label><strong>${escapeHtml(item.severity || labels.severity || "unknown")}</strong></div><div class="detail-field"><label>Server</label><strong>${escapeHtml(item.server || labels.instance || "Unknown")}</strong></div><div class="detail-field"><label>State</label><strong>${escapeHtml(item.resolved_at ? "Resolved" : item.status_text || item.action || "Firing")}</strong></div><div class="detail-field"><label>Started</label><strong>${formatTime(item.starts_at || alert.startsAt)}</strong></div><div class="detail-field"><label>Owner</label><strong>${escapeHtml(item.assignee_name || item.user_name || "Unassigned")}</strong></div><div class="detail-field"><label>Resolved by</label><strong>${escapeHtml(item.resolved_by || "—")}</strong></div></div>${annotations.description ? `<h3>Description</h3><div class="detail-description">${escapeHtml(annotations.description)}</div>` : ""}<h3>Timeline</h3>${(item.timeline || []).slice().reverse().map((event) => `<div class="timeline-item"><time>${formatTime(event.time)}${event.user_name ? ` · ${escapeHtml(event.user_name)}` : ""}</time>${escapeHtml(event.text || event.type || "Event")}</div>`).join("") || `<p class="muted">No timeline events recorded.</p>`}<h3>Notes (${(item.notes || []).length})</h3>${(item.notes || []).slice().reverse().map((note) => `<div class="note"><small>${formatTime(note.time)} · ${escapeHtml(note.user_name || "Unknown")}</small>${escapeHtml(note.text)}</div>`).join("") || `<p class="muted">No notes recorded.</p>`}`;
    $("detail-dialog").showModal();
  } catch (error) { setError(error.message); }
}

async function refresh() {
  try { setError(""); await Promise.all([loadSummary(), loadIncidents()]); } catch (error) { setError(error.message); }
}
function scheduleRefresh() {
  if (state.timer) clearInterval(state.timer);
  const seconds = Number($("refresh").value);
  if (seconds) state.timer = setInterval(refresh, seconds * 1000);
}
document.querySelectorAll(".nav-item").forEach((button) => button.addEventListener("click", () => {
  document.querySelectorAll(".nav-item").forEach((item) => item.classList.remove("active"));
  button.classList.add("active"); state.status = button.dataset.status; refresh();
}));
["search", "severity"].forEach((id) => $(id).addEventListener("input", refresh));
$("refresh").addEventListener("change", scheduleRefresh);
$("refresh-now").addEventListener("click", refresh);
$("close-dialog").addEventListener("click", () => $("detail-dialog").close());
$("detail-dialog").addEventListener("click", (event) => { if (event.target === $("detail-dialog")) $("detail-dialog").close(); });
scheduleRefresh();
refresh();
