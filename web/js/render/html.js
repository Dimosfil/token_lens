import { time } from "../format.js";

export function value(value) {
  return value || "";
}

export function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, char => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "\"": "&quot;",
    "'": "&#39;",
  }[char]));
}

export function looksLikeId(value) {
  return /^[a-z0-9_-]{12,}$/i.test(String(value || ""));
}

export function taskName(row, fallbackTsKey = "started_at") {
  const name = value(row.thread_name).trim();
  if (name && !looksLikeId(name)) return name;
  if (isMiniModelRow(row) && row.thread_id) {
    return `Mini call ${String(row.thread_id).slice(-6)}`;
  }
  if (String(row.turn_id || "").startsWith("chat:") && row.thread_id) {
    return `Chat ${String(row.thread_id).slice(-6)}`;
  }
  return `\u0417\u0430\u0434\u0430\u0447\u0430 ${time(row[fallbackTsKey])}`;
}

function isMiniModelRow(row) {
  return String(row.models || row.model || "").toLowerCase().includes("mini");
}

export function detailsTitle(lines) {
  return lines.filter(line => !line.endsWith(": ")).join("\n");
}
