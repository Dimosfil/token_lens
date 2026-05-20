import { number, time } from "../format.js";

export function renderMetrics(summary) {
  const el = document.getElementById("metrics");
  const cards = [
    ["Turns", summary.turns],
    ["Threads", summary.threads],
    ["Total tokens", summary.total_tokens],
    ["Reasoning tokens", summary.reasoning_output_tokens],
    ["Input tokens", summary.input_tokens],
    ["Cached input", summary.cached_input_tokens],
    ["Output tokens", summary.output_tokens],
    ["Latest turn", summary.latest_turn ? time(summary.latest_turn) : "-"],
  ];
  el.innerHTML = cards.map(([label, value]) => `
    <div class="metric">
      <span>${label}</span>
      <strong>${typeof value === "number" ? number(value) : value}</strong>
    </div>
  `).join("");
}
