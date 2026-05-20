import { getJson } from "./js/api.js";
import { renderDaily } from "./js/render/daily.js";
import { renderMetrics } from "./js/render/metrics.js";
import { renderModelAverages, renderModels } from "./js/render/models.js";
import { renderTasks } from "./js/render/tasks.js";
import { renderTop, renderTurns } from "./js/render/turns.js";
import { setAutoStatus } from "./js/status.js";


let dataVersion = null;
let refreshPromise = null;
const AUTO_REFRESH_MS = 5000;


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
