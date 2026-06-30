import { getJson } from "../api.js";
import { duration, number, time } from "../format.js";
import { detailsTitle, escapeHtml as sharedEscapeHtml, taskName as sharedTaskName, value as sharedValue } from "./html.js";

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
    renderTaskRows(rows, "taskRows");
    return;
  }
  document.getElementById("taskRows").innerHTML = "";
  renderAggregateTasks(rows);
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
    renderTaskRows(rows, "bucketTasks");
  } catch (err) {
    error.textContent = err.message;
  }
}

export function initBucketModal() {
  const dialog = document.getElementById("bucketDialog");
  document.getElementById("bucketClose").addEventListener("click", () => dialog.close());
}
