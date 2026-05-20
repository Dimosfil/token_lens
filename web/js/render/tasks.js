import { number, time } from "../format.js";

export function renderTasks(rows) {
  const el = document.getElementById("tasks");
  el.innerHTML = rows.map(row => `
    <tr>
      <td>${time(row.finished_at)}</td>
      <td class="thread" title="${row.turn_id}">${row.thread_name || row.thread_id}</td>
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
