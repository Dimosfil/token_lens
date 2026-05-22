import { getJson } from "../api.js";
import { duration, number, time } from "../format.js";
import { detailsTitle, escapeHtml as sharedEscapeHtml, taskName as sharedTaskName, value as sharedValue } from "./html.js";

function taskDetails(row) {
  return detailsTitle([
    `Thread ID: ${sharedValue(row.thread_id)}`,
    `Turn ID: ${sharedValue(row.turn_id)}`,
    `Source logs: ${sharedValue(row.first_source_log_id)}-${sharedValue(row.last_source_log_id)}`,
    `Submission IDs: ${sharedValue(row.submission_ids)}`,
    `Response IDs: ${sharedValue(row.response_ids)}`,
  ]);
}

function renderAggregateTasks(rows) {
  const el = document.getElementById("taskBuckets");
  el.innerHTML = rows.map(row => `
    <tr class="bucket-row" data-period="${sharedEscapeHtml(row.period)}" tabindex="0">
      <td>${sharedEscapeHtml(row.period)}</td>
      <td>${time(row.started_at)}</td>
      <td>${time(row.finished_at)}</td>
      <td>${duration(row.elapsed_seconds)}</td>
      <td>${number(row.tasks)}</td>
      <td>${row.models}</td>
      <td>${number(row.model_calls)}</td>
      <td>${number(row.total_tokens_per_call)}</td>
      <td>${number(row.total_tokens)}</td>
      <td>${number(row.input_tokens)}</td>
      <td>${number(row.cached_input_tokens)}</td>
      <td>${number(row.non_cached_input_tokens)}</td>
      <td>${number(row.output_tokens)}</td>
      <td>${number(row.reasoning_output_tokens)}</td>
      <td>${sharedValue(row.efforts)}</td>
      <td>${row.statuses}</td>
    </tr>
  `).join("");
}

function renderTaskRows(rows, targetId) {
  const el = document.getElementById(targetId);
  el.innerHTML = rows.map(row => `
    <tr class="detail-row" data-thread-id="${sharedEscapeHtml(row.thread_id)}" data-turn-id="${sharedEscapeHtml(row.turn_id)}" tabindex="0">
      <td>${time(row.finished_at)}</td>
      <td>${time(row.started_at)}</td>
      <td>${duration(row.elapsed_seconds)}</td>
      <td class="task-cell" title="${sharedEscapeHtml(taskDetails(row))}">${sharedEscapeHtml(sharedTaskName(row))}</td>
      <td>${row.models}</td>
      <td>${number(row.model_calls)}</td>
      <td>${number(row.total_tokens_per_call)}</td>
      <td>${number(row.total_tokens)}</td>
      <td>${number(row.input_tokens)}</td>
      <td>${number(row.cached_input_tokens)}</td>
      <td>${number(row.non_cached_input_tokens)}</td>
      <td>${number(row.output_tokens)}</td>
      <td>${number(row.reasoning_output_tokens)}</td>
      <td>${sharedValue(row.efforts)}</td>
      <td>${row.statuses}</td>
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
