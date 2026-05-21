import { getJson } from "./js/api.js";
import { initDetailModal, openTaskDetail } from "./js/detail-modal.js";
import { renderDaily } from "./js/render/daily.js";
import { renderMetrics } from "./js/render/metrics.js";
import { renderModelAverages, renderModels } from "./js/render/models.js";
import { renderTasks } from "./js/render/tasks.js";
import { renderTop, renderTurns } from "./js/render/turns.js";
import { setAutoStatus } from "./js/status.js";
import { initResizableTables } from "./js/table-resize.js";


let dataVersion = null;
let refreshPromise = null;
let chartMode = "total";
let lastDashboard = null;
const AUTO_REFRESH_MS = 5000;
const RANGE_SECONDS = {
  "1h": 60 * 60,
  "24h": 24 * 60 * 60,
  "7d": 7 * 24 * 60 * 60,
  "30d": 30 * 24 * 60 * 60,
  "365d": 365 * 24 * 60 * 60,
};
const BUCKET_SECONDS = {
  hour: 60 * 60,
  day: 24 * 60 * 60,
  month: 30 * 24 * 60 * 60,
};
const DEFAULT_BUCKET = "day";


function bucketAllowed(range, bucket) {
  return BUCKET_SECONDS[bucket] <= RANGE_SECONDS[range];
}


function syncBucketOptions() {
  const range = document.getElementById("rangeFilter").value;
  const bucketSelect = document.getElementById("bucketFilter");
  bucketSelect.querySelectorAll("option").forEach(option => {
    option.disabled = !bucketAllowed(range, option.value);
  });
  if (!bucketAllowed(range, bucketSelect.value)) {
    bucketSelect.value = bucketAllowed(range, DEFAULT_BUCKET) ? DEFAULT_BUCKET : "hour";
  }
}


function dashboardQuery() {
  syncBucketOptions();
  const params = new URLSearchParams();
  const model = document.getElementById("modelFilter").value;
  const range = document.getElementById("rangeFilter").value;
  const bucket = document.getElementById("bucketFilter").value;
  if (model) params.set("model", model);
  if (range) params.set("range", range);
  if (bucket) params.set("bucket", bucket);
  const query = params.toString();
  return query ? `?${query}` : "";
}


function renderDashboard(dashboard) {
  const bucket = document.getElementById("bucketFilter").value;
  renderMetrics(dashboard.summary.summary);
  renderDaily(dashboard.daily, chartMode, bucket);
  renderTurns(dashboard.turns);
  renderTasks(dashboard.tasks);
  renderTop(dashboard.summary.top_turns);
  renderModels(dashboard.models);
  renderModelAverages(dashboard.models);
  initResizableTables();
}


async function refresh(importFirst = false) {
  if (refreshPromise) return refreshPromise;

  refreshPromise = refreshNow(importFirst).finally(() => {
    refreshPromise = null;
  });
  return refreshPromise;
}


async function refreshNow(importFirst = false) {
  setAutoStatus(importFirst ? "Importing data" : "Loading data");
  const query = dashboardQuery();
  const url = importFirst ? `/api/refresh${query}` : `/api/dashboard${query}`;
  const options = importFirst ? { method: "POST" } : {};
  const dashboard = await getJson(url, options);
  lastDashboard = dashboard;
  renderDashboard(dashboard);
  dataVersion = dashboard.state.version;
  setAutoStatus(`Updated ${new Date().toLocaleTimeString("ru-RU")}`);
}


async function pollForUpdates() {
  setAutoStatus("Checking for updates");
  if (refreshPromise) return;

  getJson("/api/state")
    .then(state => {
      if (!dataVersion || state.version !== dataVersion) {
        return refresh(false);
      }
      setAutoStatus(`Checked ${new Date().toLocaleTimeString("ru-RU")}`);
      return null;
    })
    .catch(err => {
      setAutoStatus(`Auto refresh error: ${err.message}`, true);
    });
}


document.getElementById("refresh").addEventListener("click", () => refresh(true));
document.getElementById("modelFilter").addEventListener("change", () => refresh(false));
document.getElementById("rangeFilter").addEventListener("change", () => {
  syncBucketOptions();
  refresh(false);
});
document.getElementById("bucketFilter").addEventListener("change", () => refresh(false));
document.getElementById("chartMode").addEventListener("click", event => {
  const button = event.target.closest("[data-chart-mode]");
  if (!button) return;
  chartMode = button.dataset.chartMode;
  document.querySelectorAll("[data-chart-mode]").forEach(item => {
    item.classList.toggle("is-active", item === button);
  });
  if (lastDashboard) renderDashboard(lastDashboard);
});
document.addEventListener("click", event => {
  const row = event.target.closest(".detail-row");
  if (!row) return;
  openTaskDetail(row.dataset.threadId, row.dataset.turnId);
});
document.addEventListener("keydown", event => {
  if (event.key !== "Enter" && event.key !== " ") return;
  const row = event.target.closest(".detail-row");
  if (!row) return;
  event.preventDefault();
  openTaskDetail(row.dataset.threadId, row.dataset.turnId);
});

syncBucketOptions();
initDetailModal();
initResizableTables();
refresh(false).catch(err => {
  setAutoStatus(`Refresh error: ${err.message}`, true);
  document.body.insertAdjacentHTML("beforeend", `<pre>${err.message}</pre>`);
});
setInterval(pollForUpdates, AUTO_REFRESH_MS);
