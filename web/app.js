import { getJson } from "./js/api.js";
import { renderDaily } from "./js/render/daily.js";
import { renderMetrics } from "./js/render/metrics.js";
import { renderModelAverages, renderModels } from "./js/render/models.js";
import { renderTasks } from "./js/render/tasks.js";
import { renderTop, renderTurns } from "./js/render/turns.js";
import { setAutoStatus } from "./js/status.js";


let dataVersion = null;
let refreshPromise = null;
let chartMode = "total";
let lastDashboard = null;
const AUTO_REFRESH_MS = 5000;


function dashboardQuery() {
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
document.getElementById("rangeFilter").addEventListener("change", () => refresh(false));
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

refresh(false).catch(err => {
  setAutoStatus(`Refresh error: ${err.message}`, true);
  document.body.insertAdjacentHTML("beforeend", `<pre>${err.message}</pre>`);
});
setInterval(pollForUpdates, AUTO_REFRESH_MS);
