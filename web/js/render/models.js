import { number, time } from "../format.js";

export function renderModels(rows) {
  const select = document.getElementById("modelFilter");
  const current = select.value;
  select.innerHTML = `<option value="">Все модели</option>` + rows.map(row => (
    `<option value="${row.model}">${row.model} · ${number(row.total_tokens)}</option>`
  )).join("");
  select.value = current;
}

export function renderModelAverages(rows) {
  const el = document.getElementById("modelAverages");
  el.innerHTML = rows.map(row => `
    <tr>
      <td>${time(row.finished_at)}</td>
      <td class="thread" title="${row.model}">${row.model}</td>
      <td>${row.model}</td>
      <td>${row.statuses}</td>
      <td>1</td>
      <td>${number(row.total_tokens_per_call)}</td>
      <td>${number(row.avg_total_tokens)}</td>
      <td>${number(row.avg_input_tokens)}</td>
      <td>${number(row.avg_cached_input_tokens)}</td>
      <td>${number(row.avg_non_cached_input_tokens)}</td>
      <td>${number(row.avg_output_tokens)}</td>
      <td>${number(row.avg_reasoning_output_tokens)}</td>
    </tr>
  `).join("");
}
