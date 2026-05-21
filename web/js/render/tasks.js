import { getJson } from "../api.js";
import { number, time } from "../format.js";

function value(value) {
  return value || "";
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, char => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "\"": "&quot;",
    "'": "&#39;",
  }[char]));
}

function looksLikeId(value) {
  return /^[a-z0-9_-]{12,}$/i.test(String(value || ""));
}

function taskName(row) {
  const name = value(row.thread_name).trim();
  if (name && !looksLikeId(name)) return name;
  return `Задача ${time(row.started_at)}`;
}

function taskDetails(row) {
  return [
    `Thread ID: ${value(row.thread_id)}`,
    `Turn ID: ${value(row.turn_id)}`,
    `Source logs: ${value(row.first_source_log_id)}-${value(row.last_source_log_id)}`,
    `Submission IDs: ${value(row.submission_ids)}`,
    `Response IDs: ${value(row.response_ids)}`,
  ].filter(line => !line.endsWith(": ")).join("\n");
}

export function renderTasks(rows) {
  const el = document.getElementById("tasks");
  el.innerHTML = rows.map(row => `
    <tr class="bucket-row" data-period="${escapeHtml(row.period)}" tabindex="0">
      <td>${escapeHtml(row.period)}</td>
      <td>${time(row.started_at)}</td>
      <td>${time(row.finished_at)}</td>
      <td>${number(row.tasks)}</td>
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
      <td>${value(row.efforts)}</td>
    </tr>
  `).join("");
}

function renderBucketTasks(rows) {
  const el = document.getElementById("bucketTasks");
  el.innerHTML = rows.map(row => `
    <tr class="detail-row" data-thread-id="${escapeHtml(row.thread_id)}" data-turn-id="${escapeHtml(row.turn_id)}" tabindex="0">
      <td>${time(row.finished_at)}</td>
      <td>${time(row.started_at)}</td>
      <td class="task-cell" title="${escapeHtml(taskDetails(row))}">${escapeHtml(taskName(row))}</td>
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
      <td>${value(row.efforts)}</td>
    </tr>
  `).join("");
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
    renderBucketTasks(rows);
  } catch (err) {
    error.textContent = err.message;
  }
}

export function initBucketModal() {
  const dialog = document.getElementById("bucketDialog");
  document.getElementById("bucketClose").addEventListener("click", () => dialog.close());
}
