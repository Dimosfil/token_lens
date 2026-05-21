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
  return `Задача ${time(row.ts_iso)}`;
}

function taskDetails(row) {
  return [
    `Thread ID: ${value(row.thread_id)}`,
    `Turn ID: ${value(row.turn_id)}`,
    `Response ID: ${value(row.response_id)}`,
    `Submission ID: ${value(row.submission_id)}`,
    `Source log: ${value(row.source_log_id)}`,
  ].filter(line => !line.endsWith(": ")).join("\n");
}

export function renderTurns(rows) {
  const el = document.getElementById("turns");
  el.innerHTML = rows.map(row => `
    <tr>
      <td>${time(row.ts_iso)}</td>
      <td class="task-cell" title="${escapeHtml(taskDetails(row))}">${escapeHtml(taskName(row))}</td>
      <td>${row.model}</td>
      <td>${value(row.reasoning_effort)}</td>
      <td>${row.status}</td>
      <td>${number(row.total_tokens)}</td>
      <td>${number(row.input_tokens)}</td>
      <td>${number(row.cached_input_tokens)}</td>
      <td>${number(row.non_cached_input_tokens)}</td>
      <td>${number(row.output_tokens)}</td>
      <td>${number(row.reasoning_output_tokens)}</td>
    </tr>
  `).join("");
}

export function renderTop(rows) {
  const el = document.getElementById("topTurns");
  el.innerHTML = rows.map(row => `
    <div class="top-item">
      <div>
        <strong>${row.thread_name || row.thread_id}</strong><br>
        <small>${time(row.ts_iso)} · ${row.model} · ${row.response_id || row.turn_id}</small>
      </div>
      <strong>${number(row.total_tokens)}</strong>
    </div>
  `).join("");
}
