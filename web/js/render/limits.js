function resetLabel(row) {
  if (!row?.reset_at) return "-";
  const resetAt = new Date(row.reset_at);
  if (Number.isNaN(resetAt.getTime())) return "-";
  const now = new Date();
  if (resetAt.toDateString() === now.toDateString()) {
    return resetAt.toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" });
  }
  return resetAt.toLocaleDateString("ru-RU", { day: "numeric", month: "short" });
}

function percentLabel(row) {
  if (row?.remaining_percent === null || row?.remaining_percent === undefined) {
    return "-";
  }
  return `${row.remaining_percent}%`;
}

function progressWidth(row) {
  if (row?.remaining_percent === null || row?.remaining_percent === undefined) {
    return 0;
  }
  return Math.max(0, Math.min(100, row.remaining_percent));
}

function windowLabel(row) {
  if (row?.label === "weekly") return "Еженедельно";
  return row?.label || row?.key || "-";
}

function windowTitle(row) {
  const name = row?.display_name && row.display_name !== "Codex" ? `${row.display_name} ` : "";
  if (row?.label === "5h") return `${name}Лимит использования 5 часов`;
  if (row?.label === "weekly") return `${name}Недельный лимит использования`;
  return `${name}${windowLabel(row)}`;
}

function stateLabel(snapshot) {
  if (!snapshot?.ok) return "Unavailable";
  if (snapshot.cached) return "Cached";
  return snapshot.plan_type || "Live";
}

export function renderUsageLimits(snapshot) {
  const el = document.getElementById("usageLimits");
  if (!el) return;
  const limits = Array.isArray(snapshot?.windows) ? snapshot.windows : [];
  if (!limits.length) {
    el.hidden = false;
    el.innerHTML = `
      <div class="limit-widget-head">
        <span>Оставшийся лимит</span>
        <span class="limit-widget-state">${stateLabel(snapshot)}</span>
      </div>
      <p class="limit-widget-error">${snapshot?.error || "Codex app-server limits are unavailable"}</p>
    `;
    return;
  }
  el.hidden = false;
  el.innerHTML = `
    <div class="limit-widget-head">
      <span>Оставшийся лимит</span>
      <span class="limit-widget-state">${stateLabel(snapshot)}</span>
    </div>
    <div class="limit-widget-rows">
      ${limits.map(row => `
        <div class="limit-row">
          <strong>${windowTitle(row)}</strong>
          <span><b>${percentLabel(row)}</b> осталось</span>
          <time datetime="${row.reset_at || ""}">${resetLabel(row)}</time>
          <div class="limit-track" aria-hidden="true">
            <div class="limit-fill" style="width: ${progressWidth(row)}%"></div>
          </div>
        </div>
      `).join("")}
    </div>
  `;
}
