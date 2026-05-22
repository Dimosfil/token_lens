import { number, time } from "../format.js";
import { detailsTitle, escapeHtml as sharedEscapeHtml, taskName as sharedTaskName, value as sharedValue } from "./html.js";

function taskDetails(row) {
  return detailsTitle([
    `Thread ID: ${sharedValue(row.thread_id)}`,
    `Turn ID: ${sharedValue(row.turn_id)}`,
    `Response ID: ${sharedValue(row.response_id)}`,
    `Submission ID: ${sharedValue(row.submission_id)}`,
    `Source log: ${sharedValue(row.source_log_id)}`,
  ]);
}

export function renderTurns(rows) {
  const el = document.getElementById("turns");
  el.innerHTML = rows.map(row => `
    <tr class="detail-row" data-thread-id="${sharedEscapeHtml(row.thread_id)}" data-turn-id="${sharedEscapeHtml(row.turn_id)}" tabindex="0">
      <td>${time(row.ts_iso)}</td>
      <td class="task-cell" title="${sharedEscapeHtml(taskDetails(row))}">${sharedEscapeHtml(sharedTaskName(row, "ts_iso"))}</td>
      <td>${row.model}</td>
      <td>${sharedValue(row.reasoning_effort)}</td>
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
