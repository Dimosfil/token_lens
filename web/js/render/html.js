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
  return `\u0417\u0430\u0434\u0430\u0447\u0430 ${time(row[fallbackTsKey])}`;
}

export function detailsTitle(lines) {
  return lines.filter(line => !line.endsWith(": ")).join("\n");
}
