let chartMode = "total";
let taskMode = "aggregate";

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


export function getChartMode() {
  return chartMode;
}


export function setChartMode(mode) {
  chartMode = mode;
}


export function getTaskMode() {
  return taskMode;
}


export function setTaskMode(mode) {
  taskMode = mode;
}


export function applyDashboardTaskMode(dashboard) {
  taskMode = dashboard.task_modes?.active || dashboard.task_mode || taskMode;
}


export function restorePageSettings() {
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


export function savePageSettings() {
  writePageSettings({
    range: document.getElementById("rangeFilter").value,
    bucket: document.getElementById("bucketFilter").value,
    customStart: document.getElementById("customStart").value,
    customEnd: document.getElementById("customEnd").value,
    chartMode,
    taskMode,
  });
}


export function syncChartModeOptions() {
  document.querySelectorAll("[data-chart-mode]").forEach(item => {
    item.classList.toggle("is-active", item.dataset.chartMode === chartMode);
  });
}


export function syncBucketOptions() {
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


export function syncTaskModeOptions() {
  const range = document.getElementById("rangeFilter").value;
  const separateAllowed = SEPARATE_TASK_RANGES.has(range);
  const separateButton = document.querySelector("[data-task-mode='separate']");
  separateButton.disabled = !separateAllowed;
  separateButton.title = separateAllowed
    ? "\u041f\u043e\u043a\u0430\u0437\u0430\u0442\u044c \u0437\u0430\u0434\u0430\u0447\u0438 \u043e\u0442\u0434\u0435\u043b\u044c\u043d\u044b\u043c\u0438 \u0441\u0442\u0440\u043e\u043a\u0430\u043c\u0438"
    : "\u041e\u0442\u0434\u0435\u043b\u044c\u043d\u044b\u0435 \u0437\u0430\u0434\u0430\u0447\u0438 \u0434\u043e\u0441\u0442\u0443\u043f\u043d\u044b \u0442\u043e\u043b\u044c\u043a\u043e \u0434\u043b\u044f \u0447\u0430\u0441\u0430 \u0438 \u0434\u043d\u044f";
  if (!separateAllowed && taskMode === "separate") taskMode = "aggregate";
  document.querySelectorAll("[data-task-mode]").forEach(item => {
    item.classList.toggle("is-active", item.dataset.taskMode === taskMode);
  });
}


export function dashboardQuery(source = "codex") {
  syncBucketOptions();
  syncTaskModeOptions();
  const params = new URLSearchParams();
  const range = document.getElementById("rangeFilter").value;
  const bucket = document.getElementById("bucketFilter").value;
  if (range) params.set("range", range);
  if (bucket) params.set("bucket", bucket);
  params.set("source", source);
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
