import { number } from "../format.js";

export function renderDaily(rows) {
  const el = document.getElementById("dailyChart");
  const recent = rows.slice(-21);
  const max = Math.max(...recent.map(row => row.total_tokens || 0), 1);
  el.innerHTML = recent.map(row => {
    const h = Math.max(2, Math.round((row.total_tokens || 0) / max * 190));
    const day = row.day.slice(5);
    return `
      <div class="bar" title="${row.day}: ${number(row.total_tokens)} tokens">
        <div class="bar-fill" style="height:${h}px"></div>
        <label>${day}</label>
      </div>
    `;
  }).join("");
}
