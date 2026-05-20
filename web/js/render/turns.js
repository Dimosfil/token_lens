import { number, time } from "../format.js";

export function renderTurns(rows) {
  const el = document.getElementById("turns");
  el.innerHTML = rows.map(row => `
    <tr>
      <td>${time(row.ts_iso)}</td>
      <td class="thread" title="${row.thread_id}">${row.thread_name || row.thread_id}</td>
      <td>${row.model}</td>
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
        <small>${time(row.ts_iso)} В· ${row.model} В· ${row.response_id || row.turn_id}</small>
      </div>
      <strong>${number(row.total_tokens)}</strong>
    </div>
  `).join("");
}
