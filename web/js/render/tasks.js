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
    <tr>
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
    </tr>
  `).join("");
}
