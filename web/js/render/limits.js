import { number } from "../format.js";

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

function updatedLabel(snapshot) {
  const value = snapshot?.last_success_at || snapshot?.fetched_at;
  if (!value) return "";
  const updatedAt = new Date(value);
  if (Number.isNaN(updatedAt.getTime())) return "";
  const time = updatedAt.toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" });
  return snapshot?.stale ? `last updated ${time}` : `updated ${time}`;
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

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, char => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[char]));
}

function limitDisplayName(item) {
  return item?.display_name || item?.limit_name || item?.limit_id || "Codex";
}

function normalizedLimitGroups(snapshot, limits) {
  const sourceGroups = Array.isArray(snapshot?.groups) ? snapshot.groups : [];
  const groups = sourceGroups
    .map(group => ({
      ...group,
      display_name: limitDisplayName(group),
      windows: Array.isArray(group?.windows) ? group.windows : [],
    }))
    .filter(group => group.windows.length);
  if (groups.length) return groups;

  const buckets = new Map();
  limits.forEach(row => {
    const displayName = limitDisplayName(row);
    const key = `${row?.limit_id || ""}:${displayName}`;
    if (!buckets.has(key)) {
      buckets.set(key, { display_name: displayName, windows: [] });
    }
    buckets.get(key).windows.push(row);
  });
  return [...buckets.values()];
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
  if (snapshot.stale) return "Stale";
  if (snapshot.cached) return "Cached";
  return snapshot.plan_type || "Live";
}

function costLabel(value) {
  return `$${Number(value || 0).toFixed(4)}`;
}

function renderOpenCodeSpend(el, summary) {
  el.hidden = false;
  el.innerHTML = `
    <div class="limit-widget-head">
      <span>OpenCode spend</span>
      <span class="limit-widget-state">${escapeHtml(costLabel(summary?.estimated_cost))}</span>
    </div>
    <div class="limit-widget-rows">
      <div class="limit-group">
        <div class="limit-group-name">Cost</div>
        <div class="limit-group-rows">
          <div class="limit-row">
            <strong>${escapeHtml(costLabel(summary?.estimated_cost))}</strong>
            <span><b>${escapeHtml(number(summary?.total_tokens))}</b> tokens</span>
            <span><b>${escapeHtml(number(summary?.turns))}</b> calls</span>
          </div>
        </div>
      </div>
    </div>
  `;
}

export function renderUsageLimits(snapshot, source = "codex", summary = {}) {
  const el = document.getElementById("usageLimits");
  if (!el) return;
  if (source === "opencode") {
    renderOpenCodeSpend(el, summary);
    return;
  }
  const limits = Array.isArray(snapshot?.windows) ? snapshot.windows : [];
  const groups = normalizedLimitGroups(snapshot, limits);
  const updated = updatedLabel(snapshot);
  if (!groups.length) {
    el.hidden = false;
    el.innerHTML = `
      <div class="limit-widget-head">
        <span>Оставшийся лимит</span>
        <span class="limit-widget-state">${escapeHtml(stateLabel(snapshot))}</span>
      </div>
      <p class="limit-widget-error">${escapeHtml(snapshot?.error || "Codex app-server limits are unavailable")}</p>
      ${updated ? `<p class="limit-widget-meta">${escapeHtml(updated)}</p>` : ""}
    `;
    return;
  }
  el.hidden = false;
  el.innerHTML = `
    <div class="limit-widget-head">
      <span>Оставшийся лимит</span>
      <span class="limit-widget-state">${escapeHtml(stateLabel(snapshot))}</span>
    </div>
    <div class="limit-widget-rows">
      ${updated ? `<p class="limit-widget-meta">${escapeHtml(updated)}</p>` : ""}
      ${groups.map(group => `
        <div class="limit-group">
          <div class="limit-group-name" title="${escapeHtml(limitDisplayName(group))}">
            ${escapeHtml(limitDisplayName(group))}
          </div>
          <div class="limit-group-rows">
            ${group.windows.map(row => `
              <div class="limit-row">
                <strong title="${escapeHtml(windowTitle(row))}">${escapeHtml(windowLabel(row))}</strong>
                <span><b>${escapeHtml(percentLabel(row))}</b> осталось</span>
                <time datetime="${escapeHtml(row.reset_at || "")}">${escapeHtml(resetLabel(row))}</time>
                <div class="limit-track" aria-hidden="true">
                  <div class="limit-fill" style="width: ${progressWidth(row)}%"></div>
                </div>
              </div>
            `).join("")}
          </div>
        </div>
      `).join("")}
    </div>
  `;
}
