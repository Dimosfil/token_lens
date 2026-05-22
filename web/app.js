import { getJson, hasActiveRequests } from "./js/api.js";
import {
  applyDashboardTaskMode,
  dashboardQuery,
  getChartMode,
  getTaskMode,
  restorePageSettings,
  savePageSettings,
  setChartMode,
  setTaskMode,
  syncBucketOptions,
  syncChartModeOptions,
  syncTaskModeOptions,
} from "./js/dashboard-state.js";
import { initDetailModal, openTaskDetail } from "./js/detail-modal.js";
import { renderDaily } from "./js/render/daily.js";
import { renderMetrics } from "./js/render/metrics.js";
import { renderModelAverages, renderModels } from "./js/render/models.js";
import { initBucketModal, openBucketDetail, renderTasks } from "./js/render/tasks.js";
import { renderTop } from "./js/render/turns.js";
import { setAutoStatus } from "./js/status.js";
import { initResizableTables } from "./js/table-resize.js";


let dataVersion = null;
let refreshPromise = null;
let lastDashboard = null;
const AUTO_REFRESH_MS = 5000;


function renderDashboard(dashboard) {
  const bucket = document.getElementById("bucketFilter").value;
  applyDashboardTaskMode(dashboard);
  syncTaskModeOptions();
  savePageSettings();
  renderMetrics(dashboard.summary.summary);
  renderDaily(dashboard.daily, getChartMode(), bucket);
  renderTasks(dashboard.tasks, getTaskMode());
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
  if (refreshPromise || hasActiveRequests()) {
    setAutoStatus("Waiting for current request");
    return;
  }

  setAutoStatus("Checking for updates");

  getJson("/api/state")
    .then(state => {
      if (!dataVersion || state.version !== dataVersion) {
        return refresh(false);
      }
      setAutoStatus(`Checked ${new Date().toLocaleTimeString("ru-RU")}`);
      return null;
    })
    .catch(err => {
      const transient = err.message === "Failed to fetch" || err.message.startsWith("Request timed out");
      setAutoStatus(transient ? `Will retry auto refresh` : `Auto refresh error: ${err.message}`, !transient);
    });
}


document.getElementById("refresh").addEventListener("click", () => refresh(true));
document.getElementById("rangeFilter").addEventListener("change", () => {
  syncBucketOptions();
  syncTaskModeOptions();
  savePageSettings();
  refresh(false);
});
document.getElementById("bucketFilter").addEventListener("change", () => {
  savePageSettings();
  refresh(false);
});
document.getElementById("customRangeButton").addEventListener("click", () => {
  document.getElementById("rangeFilter").value = "custom";
  syncBucketOptions();
  savePageSettings();
  refresh(false);
});
document.getElementById("customStart").addEventListener("change", () => {
  savePageSettings();
  refresh(false);
});
document.getElementById("customEnd").addEventListener("change", () => {
  savePageSettings();
  refresh(false);
});
document.getElementById("chartMode").addEventListener("click", event => {
  const button = event.target.closest("[data-chart-mode]");
  if (!button) return;
  setChartMode(button.dataset.chartMode);
  syncChartModeOptions();
  savePageSettings();
  if (lastDashboard) renderDashboard(lastDashboard);
});
document.getElementById("taskMode").addEventListener("click", event => {
  const button = event.target.closest("[data-task-mode]");
  if (!button || button.disabled) return;
  setTaskMode(button.dataset.taskMode);
  syncTaskModeOptions();
  savePageSettings();
  refresh(false);
});
document.addEventListener("click", event => {
  const bucketRow = event.target.closest(".bucket-row");
  if (bucketRow) {
    openBucketDetail(bucketRow.dataset.period, dashboardQuery());
    return;
  }
  const row = event.target.closest(".detail-row");
  if (!row) return;
  openTaskDetail(row.dataset.threadId, row.dataset.turnId);
});
document.addEventListener("keydown", event => {
  if (event.key !== "Enter" && event.key !== " ") return;
  const bucketRow = event.target.closest(".bucket-row");
  if (bucketRow) {
    event.preventDefault();
    openBucketDetail(bucketRow.dataset.period, dashboardQuery());
    return;
  }
  const row = event.target.closest(".detail-row");
  if (!row) return;
  event.preventDefault();
  openTaskDetail(row.dataset.threadId, row.dataset.turnId);
});

restorePageSettings();
syncBucketOptions();
syncTaskModeOptions();
syncChartModeOptions();
savePageSettings();
initDetailModal();
initBucketModal();
initResizableTables();
refresh(false).catch(err => {
  setAutoStatus(`Refresh error: ${err.message}`, true);
  document.body.insertAdjacentHTML("beforeend", `<pre>${err.message}</pre>`);
});
setInterval(pollForUpdates, AUTO_REFRESH_MS);
