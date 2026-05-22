import { getJson, hasActiveRequests } from "./js/api.js";
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
let chartMode = "total";
let taskMode = "aggregate";
let lastDashboard = null;
const AUTO_REFRESH_MS = 5000;
const PAGE_SETTINGS_KEY = "token-lens:page-settings:v1";
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
const SEPARATE_TASK_RANGES = new Set(["1h", "24h"]);


function readPageSettings() {
  try {
    return JSON.parse(localStorage.getItem(PAGE_SETTINGS_KEY) || "{}");
  } catch {
    return {};
  }
}


function writePageSettings(settings) {
  localStorage.setItem(PAGE_SETTINGS_KEY, JSON.stringify(settings));
}


function hasOption(select, value) {
  return Array.from(select.options).some(option => option.value === value);
}


function restorePageSettings() {
  const settings = readPageSettings();
  const range = document.getElementById("rangeFilter");
  const bucket = document.getElementById("bucketFilter");
  if (settings.range && hasOption(range, settings.range)) range.value = settings.range;
  if (settings.bucket && hasOption(bucket, settings.bucket)) bucket.value = settings.bucket;
  if (settings.customStart) document.getElementById("customStart").value = settings.customStart;
  if (settings.customEnd) document.getElementById("customEnd").value = settings.customEnd;
  if (settings.chartMode) chartMode = settings.chartMode;
  if (settings.taskMode) taskMode = settings.taskMode;
}


function savePageSettings() {
  writePageSettings({
    range: document.getElementById("rangeFilter").value,
    bucket: document.getElementById("bucketFilter").value,
    customStart: document.getElementById("customStart").value,
    customEnd: document.getElementById("customEnd").value,
    chartMode,
    taskMode,
  });
}


function syncChartModeOptions() {
  document.querySelectorAll("[data-chart-mode]").forEach(item => {
    item.classList.toggle("is-active", item.dataset.chartMode === chartMode);
  });
}


function bucketAllowed(range, bucket) {
  if (range === "custom") return bucket in BUCKET_SECONDS;
  return BUCKET_SECONDS[bucket] <= RANGE_SECONDS[range];
}


function localDateValue(date) {
  const offsetDate = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
  return offsetDate.toISOString().slice(0, 10);
}


function dateStartTs(value) {
  return Math.floor(new Date(`${value}T00:00:00`).getTime() / 1000);
}


function dateEndTs(value) {
  return Math.floor(new Date(`${value}T23:59:59`).getTime() / 1000);
}


function ensureCustomDates() {
  const start = document.getElementById("customStart");
  const end = document.getElementById("customEnd");
  if (!end.value) end.value = localDateValue(new Date());
  if (!start.value) {
    const date = new Date();
    date.setDate(date.getDate() - 7);
    start.value = localDateValue(date);
  }
}


function syncBucketOptions() {
  const range = document.getElementById("rangeFilter").value;
  const bucketSelect = document.getElementById("bucketFilter");
  document.getElementById("customRange").hidden = range !== "custom";
  if (range === "custom") ensureCustomDates();
  bucketSelect.querySelectorAll("option").forEach(option => {
    option.disabled = !bucketAllowed(range, option.value);
  });
  if (!bucketAllowed(range, bucketSelect.value)) {
    bucketSelect.value = bucketAllowed(range, DEFAULT_BUCKET) ? DEFAULT_BUCKET : "hour";
  }
}

function syncTaskModeOptions() {
  const range = document.getElementById("rangeFilter").value;
  const separateAllowed = SEPARATE_TASK_RANGES.has(range);
  const separateButton = document.querySelector("[data-task-mode='separate']");
  separateButton.disabled = !separateAllowed;
  separateButton.title = separateAllowed
    ? "Показать задачи отдельными строками"
    : "Отдельные задачи доступны только для часа и дня";
  if (!separateAllowed && taskMode === "separate") taskMode = "aggregate";
  document.querySelectorAll("[data-task-mode]").forEach(item => {
    item.classList.toggle("is-active", item.dataset.taskMode === taskMode);
  });
}


function dashboardQuery() {
  syncBucketOptions();
  syncTaskModeOptions();
  const params = new URLSearchParams();
  const range = document.getElementById("rangeFilter").value;
  const bucket = document.getElementById("bucketFilter").value;
  if (range) params.set("range", range);
  if (bucket) params.set("bucket", bucket);
  if (taskMode) params.set("task_mode", taskMode);
  if (range === "custom") {
    const start = document.getElementById("customStart").value;
    const end = document.getElementById("customEnd").value;
    if (start && end) {
      params.set("start_ts", String(dateStartTs(start)));
      params.set("end_ts", String(dateEndTs(end)));
    }
  }
  const query = params.toString();
  return query ? `?${query}` : "";
}


function renderDashboard(dashboard) {
  const bucket = document.getElementById("bucketFilter").value;
  taskMode = dashboard.task_modes?.active || dashboard.task_mode || taskMode;
  syncTaskModeOptions();
  savePageSettings();
  renderMetrics(dashboard.summary.summary);
  renderDaily(dashboard.daily, chartMode, bucket);
  renderTasks(dashboard.tasks, taskMode);
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
  chartMode = button.dataset.chartMode;
  syncChartModeOptions();
  savePageSettings();
  if (lastDashboard) renderDashboard(lastDashboard);
});
document.getElementById("taskMode").addEventListener("click", event => {
  const button = event.target.closest("[data-task-mode]");
  if (!button || button.disabled) return;
  taskMode = button.dataset.taskMode;
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
