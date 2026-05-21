import { number } from "../format.js";

function chartValue(row, mode) {
  if (mode === "per-call") return row.total_tokens_per_call || 0;
  return row.total_tokens || 0;
}

function chartLabel(row, bucket) {
  const period = row.period || row.day || "";
  if (bucket === "hour") return period.slice(5, 16);
  if (bucket === "month") return period.slice(2);
  return period.slice(5) || period;
}

function text(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function tooltipRows(row, value, unit) {
  const cached = row.cached_input_tokens || 0;
  const input = row.input_tokens || 0;
  const nonCached = Math.max(input - cached, 0);
  const cost = Number(row.estimated_cost || 0);
  return [
    ["Value", `${number(value)} ${unit}`],
    ["Calls", number(row.turns)],
    ["Input", number(input)],
    ["Cached", number(cached)],
    ["Non-cached", number(nonCached)],
    ["Output", number(row.output_tokens)],
    ["Reasoning", number(row.reasoning_output_tokens)],
    ["Cost", cost ? `$${cost.toFixed(4)}` : "$0"],
  ];
}

export function renderDaily(rows, mode = "total", bucket = "day") {
  const el = document.getElementById("dailyChart");
  el.dataset.bucket = bucket;
  const max = Math.max(...rows.map(row => chartValue(row, mode)), 1);
  if (!rows.length) {
    el.innerHTML = `<div class="empty-chart">Нет данных</div>`;
    return;
  }
  el.innerHTML = rows.map(row => {
    const value = chartValue(row, mode);
    const h = Math.max(2, Math.round(value / max * 190));
    const period = row.period || row.day;
    const label = chartLabel(row, bucket);
    const unit = mode === "per-call" ? "tokens / call" : "tokens";
    const details = tooltipRows(row, value, unit)
      .map(([name, detail]) => `
          <div>
            <span>${text(name)}</span>
            <strong>${text(detail)}</strong>
          </div>
        `)
      .join("");
    return `
      <div class="bar" tabindex="0" aria-label="${text(period)}: ${number(value)} ${unit}">
        <div class="bar-fill" style="height:${h}px"></div>
        <div class="bar-tooltip" role="tooltip">
          <b>${text(period)}</b>
          ${details}
        </div>
        <label>${text(label)}</label>
      </div>
    `;
  }).join("");
}
