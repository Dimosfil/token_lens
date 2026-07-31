import { getJson } from "../api.js";
import { duration, number, time } from "../format.js";
import { detailsTitle, escapeHtml as sharedEscapeHtml, taskName as sharedTaskName, value as sharedValue } from "./html.js";

const TEXT_COLLATOR = new Intl.Collator("ru", { numeric: true, sensitivity: "base" });
const TASK_TABLES = {
  taskAggregateTable: {
    targetId: "taskBuckets",
    defaultSort: { key: "period", direction: "desc" },
    columns: [
      ["period", "text"], ["started_at", "date"], ["finished_at", "date"],
      ["elapsed_seconds", "number"], ["tasks", "number"], ["models", "text"],
      ["model_calls", "number"], ["total_tokens_per_call", "number"],
      ["total_tokens", "number"], ["input_tokens", "number"],
      ["cached_input_tokens", "number"], ["non_cached_input_tokens", "number"],
      ["output_tokens", "number"], ["reasoning_output_tokens", "number"],
      ["efforts", "text"], ["statuses", "text"],
    ],
  },
  taskSeparateTable: {
    targetId: "taskRows",
    defaultSort: { key: "finished_at", direction: "desc" },
    columns: [
      ["finished_at", "date"], ["started_at", "date"], ["elapsed_seconds", "number"],
      ["task_name", "text"], ["models", "text"], ["model_calls", "number"],
      ["total_tokens_per_call", "number"], ["total_tokens", "number"],
      ["input_tokens", "number"], ["cached_input_tokens", "number"],
      ["non_cached_input_tokens", "number"], ["output_tokens", "number"],
      ["reasoning_output_tokens", "number"], ["efforts", "text"], ["statuses", "text"],
    ],
  },
  bucketTasksTable: {
    targetId: "bucketTasks",
    defaultSort: { key: "finished_at", direction: "desc" },
    columns: [
      ["finished_at", "date"], ["started_at", "date"], ["elapsed_seconds", "number"],
      ["task_name", "text"], ["models", "text"], ["model_calls", "number"],
      ["total_tokens_per_call", "number"], ["total_tokens", "number"],
      ["input_tokens", "number"], ["cached_input_tokens", "number"],
      ["non_cached_input_tokens", "number"], ["output_tokens", "number"],
      ["reasoning_output_tokens", "number"], ["efforts", "text"], ["statuses", "text"],
    ],
  },
};
const taskSortState = Object.fromEntries(
  Object.entries(TASK_TABLES).map(([tableId, config]) => [tableId, { ...config.defaultSort }]),
);
const taskRowsCache = {
  taskAggregateTable: [],
  taskSeparateTable: [],
  bucketTasksTable: [],
};

function sortValue(row, key, type) {
  if (key === "task_name") return sharedTaskName(row);
  if (type === "number" && !hasUsage(row) && key !== "elapsed_seconds") return null;
  const value = row[key];
  if (value == null || value === "") return null;
  if (Array.isArray(value)) return value.join(", ");
  if (type === "date") {
    const timestamp = Date.parse(value);
    return Number.isFinite(timestamp) ? timestamp : null;
  }
  if (type === "number") {
    const numeric = Number(value);
    return Number.isFinite(numeric) ? numeric : null;
  }
  return String(value);
}

function compareValues(left, right, type) {
  if (type === "text") return TEXT_COLLATOR.compare(String(left), String(right));
  return left - right;
}

export function sortTaskRows(rows, sort, columns) {
  const type = columns.find(([key]) => key === sort.key)?.[1] || "text";
  const multiplier = sort.direction === "asc" ? 1 : -1;
  return rows
    .map((row, index) => ({ row, index, value: sortValue(row, sort.key, type) }))
    .sort((left, right) => {
      const leftMissing = left.value == null || left.value === "";
      const rightMissing = right.value == null || right.value === "";
      if (leftMissing !== rightMissing) return leftMissing ? 1 : -1;
      if (leftMissing) return left.index - right.index;
      const compared = compareValues(left.value, right.value, type) * multiplier;
      return compared || left.index - right.index;
    })
    .map(item => item.row);
}

function sortedRows(tableId) {
  const config = TASK_TABLES[tableId];
  return sortTaskRows(taskRowsCache[tableId], taskSortState[tableId], config.columns);
}

function updateSortHeaders(tableId) {
  const table = document.getElementById(tableId);
  const active = taskSortState[tableId];
  table.querySelectorAll("thead th[data-sort-key]").forEach(th => {
    const selected = th.dataset.sortKey === active.key;
    th.setAttribute("aria-sort", selected ? (active.direction === "asc" ? "ascending" : "descending") : "none");
    const indicator = th.querySelector(":scope > .sort-indicator");
    if (indicator) indicator.textContent = selected ? (active.direction === "asc" ? "↑" : "↓") : "";
  });
}

function renderSortedTable(tableId) {
  if (tableId === "taskAggregateTable") renderAggregateTasks(sortedRows(tableId));
  else renderTaskRows(sortedRows(tableId), TASK_TABLES[tableId].targetId);
  updateSortHeaders(tableId);
}

function changeSort(tableId, key) {
  const config = TASK_TABLES[tableId];
  const type = config.columns.find(([columnKey]) => columnKey === key)?.[1] || "text";
  const current = taskSortState[tableId];
  taskSortState[tableId] = current.key === key
    ? { key, direction: current.direction === "desc" ? "asc" : "desc" }
    : { key, direction: type === "text" ? "asc" : "desc" };
  renderSortedTable(tableId);
}

function activateSort(event, tableId) {
  if (event.target.closest(".col-resizer")) return;
  const th = event.target.closest("th[data-sort-key]");
  if (!th) return;
  changeSort(tableId, th.dataset.sortKey);
}

export function initTaskSorting() {
  Object.entries(TASK_TABLES).forEach(([tableId, config]) => {
    const table = document.getElementById(tableId);
    if (!table || table.dataset.sortReady) return;
    table.dataset.sortReady = "true";
    const headers = Array.from(table.querySelectorAll("thead th"));
    config.columns.forEach(([key], index) => {
      const th = headers[index];
      if (!th) return;
      th.dataset.sortKey = key;
      th.tabIndex = 0;
      th.title = "Sort column; drag to reorder";
      const indicator = document.createElement("span");
      indicator.className = "sort-indicator";
      indicator.setAttribute("aria-hidden", "true");
      th.appendChild(indicator);
    });
    table.addEventListener("click", event => activateSort(event, tableId));
    table.addEventListener("keydown", event => {
      if (event.key !== "Enter" && event.key !== " ") return;
      if (!event.target.matches("th[data-sort-key]")) return;
      event.preventDefault();
      changeSort(tableId, event.target.dataset.sortKey);
    });
    updateSortHeaders(tableId);
  });
}

function taskDetails(row) {
  return detailsTitle([
    `Thread ID: ${sharedValue(row.thread_id)}`,
    `Turn ID: ${sharedValue(row.turn_id)}`,
    `Source logs: ${sharedValue(row.first_source_log_id)}-${sharedValue(row.last_source_log_id)}`,
    `Raw events: ${sharedValue(row.raw_event_calls)}`,
    `Submission IDs: ${sharedValue(row.submission_ids)}`,
    `Response IDs: ${sharedValue(row.response_ids)}`,
  ]);
}

function hasUsage(row) {
  return row.has_usage !== 0 && row.has_usage !== false;
}

function metricNumber(row, key) {
  return hasUsage(row) ? number(row[key]) : "-";
}

function calls(row) {
  return hasUsage(row) ? number(row.model_calls) : "-";
}

function taskDuration(row) {
  return hasUsage(row) ? duration(row.elapsed_seconds) : "-";
}

function status(row) {
  if (hasUsage(row)) return sharedEscapeHtml(row.statuses);
  const events = number(row.raw_event_calls);
  return `<span class="status-pill status-missing" title="${events} raw events without usage metadata">Usage missing</span>`;
}

function renderAggregateTasks(rows) {
  const el = document.getElementById("taskBuckets");
  el.innerHTML = rows.map(row => `
    <tr class="bucket-row" data-period="${sharedEscapeHtml(row.period)}" tabindex="0">
      <td>${sharedEscapeHtml(row.period)}</td>
      <td>${time(row.started_at)}</td>
      <td>${time(row.finished_at)}</td>
      <td>${taskDuration(row)}</td>
      <td>${number(row.tasks)}</td>
      <td>${row.models}</td>
      <td>${calls(row)}</td>
      <td>${metricNumber(row, "total_tokens_per_call")}</td>
      <td>${metricNumber(row, "total_tokens")}</td>
      <td>${metricNumber(row, "input_tokens")}</td>
      <td>${metricNumber(row, "cached_input_tokens")}</td>
      <td>${metricNumber(row, "non_cached_input_tokens")}</td>
      <td>${metricNumber(row, "output_tokens")}</td>
      <td>${metricNumber(row, "reasoning_output_tokens")}</td>
      <td>${sharedValue(row.efforts)}</td>
      <td>${status(row)}</td>
    </tr>
  `).join("");
}

function renderTaskRows(rows, targetId) {
  const el = document.getElementById(targetId);
  el.innerHTML = rows.map(row => `
    <tr class="detail-row ${hasUsage(row) ? "" : "is-missing-usage"}" data-thread-id="${sharedEscapeHtml(row.thread_id)}" data-turn-id="${sharedEscapeHtml(row.turn_id)}" data-has-usage="${hasUsage(row) ? "1" : "0"}" tabindex="0">
      <td>${time(row.finished_at)}</td>
      <td>${time(row.started_at)}</td>
      <td>${taskDuration(row)}</td>
      <td class="task-cell" title="${sharedEscapeHtml(taskDetails(row))}">${sharedEscapeHtml(sharedTaskName(row))}</td>
      <td>${row.models}</td>
      <td>${calls(row)}</td>
      <td>${metricNumber(row, "total_tokens_per_call")}</td>
      <td>${metricNumber(row, "total_tokens")}</td>
      <td>${metricNumber(row, "input_tokens")}</td>
      <td>${metricNumber(row, "cached_input_tokens")}</td>
      <td>${metricNumber(row, "non_cached_input_tokens")}</td>
      <td>${metricNumber(row, "output_tokens")}</td>
      <td>${metricNumber(row, "reasoning_output_tokens")}</td>
      <td>${sharedValue(row.efforts)}</td>
      <td>${status(row)}</td>
    </tr>
  `).join("");
}

export function renderTasks(rows, mode = "aggregate") {
  const aggregateTable = document.getElementById("taskAggregateTable");
  const separateTable = document.getElementById("taskSeparateTable");
  const separate = mode === "separate";
  aggregateTable.hidden = separate;
  separateTable.hidden = !separate;
  if (separate) {
    document.getElementById("taskBuckets").innerHTML = "";
    taskRowsCache.taskSeparateTable = [...rows];
    renderSortedTable("taskSeparateTable");
    return;
  }
  document.getElementById("taskRows").innerHTML = "";
  taskRowsCache.taskAggregateTable = [...rows];
  renderSortedTable("taskAggregateTable");
}

export async function openBucketDetail(period, query) {
  const dialog = document.getElementById("bucketDialog");
  const error = document.getElementById("bucketError");
  document.getElementById("bucketTitle").textContent = `Bucket ${period}`;
  document.getElementById("bucketTasks").innerHTML = "";
  error.textContent = "";
  dialog.showModal();

  try {
    const separator = query ? "&" : "?";
    const rows = await getJson(`/api/bucket-tasks${query}${separator}period=${encodeURIComponent(period)}`);
    taskRowsCache.bucketTasksTable = [...rows];
    renderSortedTable("bucketTasksTable");
  } catch (err) {
    error.textContent = err.message;
  }
}

export function initBucketModal() {
  const dialog = document.getElementById("bucketDialog");
  document.getElementById("bucketClose").addEventListener("click", () => dialog.close());
}
