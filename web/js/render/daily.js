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

export function renderDaily(rows, mode = "total", bucket = "day") {
  const el = document.getElementById("dailyChart");
  const recent = rows.slice(-24);
  const max = Math.max(...recent.map(row => chartValue(row, mode)), 1);
  if (!recent.length) {
    el.innerHTML = `<div class="empty-chart">Нет данных</div>`;
    return;
  }
  el.innerHTML = recent.map(row => {
    const value = chartValue(row, mode);
    const h = Math.max(2, Math.round(value / max * 190));
    const period = row.period || row.day;
    const label = chartLabel(row, bucket);
    const unit = mode === "per-call" ? "tokens / call" : "tokens";
    return `
      <div class="bar" title="${period}: ${number(value)} ${unit}">
        <div class="bar-fill" style="height:${h}px"></div>
        <label>${label}</label>
      </div>
    `;
  }).join("");
}
