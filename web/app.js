const fmt = new Intl.NumberFormat("ru-RU");

function number(value) {
  return fmt.format(value || 0);
}

function time(value) {
  if (!value) return "";
  return new Date(value).toLocaleString("ru-RU");
}

async function getJson(url, options) {
  const res = await fetch(url, options);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

let dataVersion = null;
let refreshPromise = null;
const AUTO_REFRESH_MS = 5000;

function setAutoStatus(message, isError = false) {
  const el = document.getElementById("autoStatus");
  if (!el) return;
  el.textContent = message;
  el.classList.toggle("is-error", isError);
}

function renderMetrics(summary) {
  const el = document.getElementById("metrics");
  const cards = [
    ["Turns", summary.turns],
    ["Threads", summary.threads],
    ["Total tokens", summary.total_tokens],
    ["Reasoning tokens", summary.reasoning_output_tokens],
    ["Input tokens", summary.input_tokens],
    ["Cached input", summary.cached_input_tokens],
    ["Output tokens", summary.output_tokens],
    ["Latest turn", summary.latest_turn ? time(summary.latest_turn) : "-"],
  ];
  el.innerHTML = cards.map(([label, value]) => `
    <div class="metric">
      <span>${label}</span>
      <strong>${typeof value === "number" ? number(value) : value}</strong>
    </div>
  `).join("");
}

function renderDaily(rows) {
  const el = document.getElementById("dailyChart");
  const recent = rows.slice(-21);
  const max = Math.max(...recent.map(row => row.total_tokens || 0), 1);
  el.innerHTML = recent.map(row => {
    const h = Math.max(2, Math.round((row.total_tokens || 0) / max * 190));
    const day = row.day.slice(5);
    return `
      <div class="bar" title="${row.day}: ${number(row.total_tokens)} tokens">
        <div class="bar-fill" style="height:${h}px"></div>
        <label>${day}</label>
      </div>
    `;
  }).join("");
}

function renderTurns(rows) {
  const el = document.getElementById("turns");
  el.innerHTML = rows.map(row => `
    <tr>
      <td>${time(row.ts_iso)}</td>
      <td class="thread" title="${row.thread_id}">${row.thread_name || row.thread_id}</td>
      <td>${row.model}</td>
      <td>${row.status}</td>
      <td>${number(row.total_tokens)}</td>
      <td>${number(row.input_tokens)}</td>
      <td>${number(row.cached_input_tokens)}</td>
      <td>${number(row.non_cached_input_tokens)}</td>
      <td>${number(row.output_tokens)}</td>
      <td>${number(row.reasoning_output_tokens)}</td>
    </tr>
  `).join("");
}

function renderTasks(rows) {
  const el = document.getElementById("tasks");
  el.innerHTML = rows.map(row => `
    <tr>
      <td>${time(row.finished_at)}</td>
      <td class="thread" title="${row.turn_id}">${row.thread_name || row.thread_id}</td>
      <td>${row.models}</td>
      <td>${row.statuses}</td>
      <td>${number(row.model_calls)}</td>
      <td>${number(row.total_tokens_per_call)}</td>
      <td>${number(row.total_tokens)}</td>
      <td>${number(row.input_tokens)}</td>
      <td>${number(row.cached_input_tokens)}</td>
      <td>${number(row.non_cached_input_tokens)}</td>
      <td>${number(row.output_tokens)}</td>
      <td>${number(row.reasoning_output_tokens)}</td>
    </tr>
  `).join("");
}

function renderTop(rows) {
  const el = document.getElementById("topTurns");
  el.innerHTML = rows.map(row => `
    <div class="top-item">
      <div>
        <strong>${row.thread_name || row.thread_id}</strong><br>
        <small>${time(row.ts_iso)} · ${row.model} · ${row.response_id || row.turn_id}</small>
      </div>
      <strong>${number(row.total_tokens)}</strong>
    </div>
  `).join("");
}

function renderModels(rows) {
  const select = document.getElementById("modelFilter");
  const current = select.value;
  select.innerHTML = `<option value="">Все модели</option>` + rows.map(row => (
    `<option value="${row.model}">${row.model} · ${number(row.total_tokens)}</option>`
  )).join("");
  select.value = current;
}

function renderModelAverages(rows) {
  const el = document.getElementById("modelAverages");
  el.innerHTML = rows.map(row => `
    <tr>
      <td>${time(row.finished_at)}</td>
      <td class="thread" title="${row.model}">${row.model}</td>
      <td>${row.model}</td>
      <td>${row.statuses}</td>
      <td>1</td>
      <td>${number(row.total_tokens_per_call)}</td>
      <td>${number(row.avg_total_tokens)}</td>
      <td>${number(row.avg_input_tokens)}</td>
      <td>${number(row.avg_cached_input_tokens)}</td>
      <td>${number(row.avg_non_cached_input_tokens)}</td>
      <td>${number(row.avg_output_tokens)}</td>
      <td>${number(row.avg_reasoning_output_tokens)}</td>
    </tr>
  `).join("");
}

async function refresh(importFirst = false) {
  if (refreshPromise) return refreshPromise;

  refreshPromise = refreshNow(importFirst).finally(() => {
    refreshPromise = null;
  });
  return refreshPromise;
}

async function refreshNow(importFirst = false) {
  const model = document.getElementById("modelFilter").value;
  const query = model ? `?model=${encodeURIComponent(model)}` : "";
  const dashboard = await getJson(`/api/refresh${query}`, { method: "POST" });
  renderMetrics(dashboard.summary.summary);
  renderDaily(dashboard.daily);
  renderTurns(dashboard.turns);
  renderTasks(dashboard.tasks);
  renderTop(dashboard.summary.top_turns);
  renderModels(dashboard.models);
  renderModelAverages(dashboard.models);
  dataVersion = dashboard.state.version;
  setAutoStatus(`Updated ${new Date().toLocaleTimeString("ru-RU")}`);
}

async function pollForUpdates() {
  setAutoStatus("Checking for updates");
  refresh(true)
    .catch(err => {
      setAutoStatus(`Auto refresh error: ${err.message}`, true);
    });
}

document.getElementById("refresh").addEventListener("click", () => refresh(true));
document.getElementById("modelFilter").addEventListener("change", () => refresh(false));

refresh(false).catch(err => {
  document.body.insertAdjacentHTML("beforeend", `<pre>${err.message}</pre>`);
});
setInterval(pollForUpdates, AUTO_REFRESH_MS);
