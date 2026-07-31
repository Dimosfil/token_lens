import { getJson } from "./api.js";
import { number, time } from "./format.js";
import { escapeHtml } from "./render/html.js";

let detail = null;
let selectedCall = 0;
const copyResetTimers = new WeakMap();
const compactNumber = new Intl.NumberFormat("ru-RU", {
  notation: "compact",
  maximumFractionDigits: 1,
});

function pretty(value, emptyMessage = "No captured payload") {
  if (value == null || value === "") return emptyMessage;
  if (typeof value === "string") return value;
  return JSON.stringify(value, null, 2);
}

function compactPayload(value) {
  if (value == null || value === "") return "";
  if (typeof value === "string") return value;
  try {
    return JSON.stringify(value);
  } catch {
    return pretty(value, "");
  }
}

function joinList(value) {
  if (Array.isArray(value)) return value.join(", ");
  return value || "";
}

function metric(label, value) {
  return `<div class="detail-metric"><span>${label}</span><strong>${escapeHtml(value)}</strong></div>`;
}

function isTokenUsageEvent(call) {
  return call?.event?.type === "codex.post_sampling_token_usage";
}

function eventLabel(call) {
  if (!call?.raw_event_captured) return "Missing";
  return isTokenUsageEvent(call) ? "Usage only" : "Captured";
}

function breakdownNumber(call, key) {
  if (call?.token_breakdown_available === false || isTokenUsageEvent(call)) return "—";
  return number(call?.[key]);
}

function emptyPayloadMessage(kind, call) {
  if (isTokenUsageEvent(call)) {
    return `No ${kind} payload: this row is a token-usage event only.`;
  }
  return `No captured ${kind} payload`;
}

function estimateRequestTokens(value) {
  const text = compactPayload(value).trim();
  if (!text) return 0;

  const chars = text.length;
  const cjkChars = (text.match(/[\u3040-\u30ff\u3400-\u9fff\uf900-\ufaff]/g) || []).length;
  const punctuationChars = (text.match(/[{}\[\]":,]/g) || []).length;
  const lineBreaks = (text.match(/\n/g) || []).length;
  const whitespaceChars = (text.match(/\s/g) || []).length;
  const compactChars = Math.max(chars - whitespaceChars, 0);
  const jsonLike = punctuationChars > chars * 0.08 || (text.startsWith("{") && text.includes("\"model\""));

  if (cjkChars > chars * 0.2) {
    return Math.max(1, Math.round(cjkChars + (chars - cjkChars) / 3.2));
  }

  const divisor = jsonLike ? 1.7 : 3.8;
  const linePenalty = jsonLike ? lineBreaks * 0.15 : lineBreaks * 0.05;
  return Math.max(1, Math.round(compactChars / divisor + linePenalty));
}

function signedNumber(value) {
  if (!Number.isFinite(value) || value === 0) return "0";
  return `${value > 0 ? "+" : ""}${number(value)}`;
}

function formatCompactTokens(value, prefix = "~") {
  if (!Number.isFinite(value) || value <= 0) return null;
  return `${prefix}${compactNumber.format(value)} tok`;
}

function setCopyButtonBaseLabel(button, label) {
  button.dataset.copyLabel = label;
  button.textContent = label;
}

function renderRequestStats(call) {
  const stats = document.getElementById("detailRequestStats");
  const requestButton = document.querySelector('[data-copy-target="detailRequest"]');
  const eventButton = document.querySelector('[data-copy-target="detailEvent"]');
  if (!stats || !requestButton || !eventButton) return;

  if (!call) {
    stats.textContent = "";
    stats.className = "payload-stats";
    setCopyButtonBaseLabel(requestButton, "Copy");
    setCopyButtonBaseLabel(eventButton, "Copy");
    return;
  }

  const requestEstimate = estimateRequestTokens(call.request);
  const tableTotal = Number(call.total_tokens || 0);
  const eventEstimate = Number(call.event?.estimated_token_count || 0);
  const delta = requestEstimate && tableTotal ? requestEstimate - tableTotal : 0;
  const ratio = requestEstimate && tableTotal ? Math.abs(delta) / tableTotal : null;
  const isClose = ratio != null && ratio <= 0.12;

  const parts = [];
  if (requestEstimate > 0) parts.push(`Request est. ${number(requestEstimate)}`);
  if (tableTotal > 0) parts.push(`Table total ${number(tableTotal)}`);
  if (requestEstimate > 0 && tableTotal > 0) parts.push(`Delta ${signedNumber(delta)}`);
  if (eventEstimate > 0) parts.push(`Event est. ${number(eventEstimate)}`);
  stats.textContent = parts.join(" · ");
  stats.className = `payload-stats${requestEstimate > 0 && tableTotal > 0 ? (isClose ? " is-close" : " is-drift") : ""}`;

  setCopyButtonBaseLabel(requestButton, `Copy ${formatCompactTokens(requestEstimate) || ""}`.trim());
  setCopyButtonBaseLabel(eventButton, `Copy ${formatCompactTokens(eventEstimate, "") || ""}`.trim());
}

function renderMeta(task) {
  const el = document.getElementById("detailMeta");
  if (!task) {
    el.innerHTML = "";
    return;
  }
  const stateTokens = Number(task.state_tokens_used || 0);
  const totalTokens = Number(task.total_tokens || 0);
  const stateMetric = stateTokens > 0 && stateTokens !== totalTokens
    ? metric("Session state estimate", number(stateTokens))
    : "";
  el.innerHTML = [
    metric("Start", time(task.started_at)),
    metric("Finish", time(task.finished_at)),
    metric("Calls", number(task.model_calls)),
    metric("Total tokens", number(task.total_tokens)),
    stateMetric,
    metric("Total / call", number(task.total_tokens_per_call)),
    metric("Raw events", `${number(task.raw_event_calls)} / ${number(task.model_calls)}`),
    metric("Models", joinList(task.models)),
    metric("Statuses", joinList(task.statuses)),
    metric("Thread", task.thread_name || task.thread_id),
    metric("Turn ID", task.turn_id),
    metric("Responses", joinList(task.response_ids)),
  ].join("");
}

function renderCalls(calls) {
  const el = document.getElementById("detailCalls");
  el.innerHTML = calls.map((call, index) => `
    <tr class="${index === selectedCall ? "is-selected" : ""}" data-call-index="${index}" tabindex="0">
      <td>${time(call.ts_iso)}</td>
      <td>${escapeHtml(call.model)}</td>
      <td>${escapeHtml(call.status)}</td>
      <td>${number(call.total_tokens)}</td>
      <td>${breakdownNumber(call, "input_tokens")}</td>
      <td>${breakdownNumber(call, "cached_input_tokens")}</td>
      <td>${breakdownNumber(call, "output_tokens")}</td>
      <td>${breakdownNumber(call, "reasoning_output_tokens")}</td>
      <td><span class="raw-event raw-event-${call.raw_event_captured ? "captured" : "missing"}">${eventLabel(call)}</span></td>
      <td class="mono">${escapeHtml(call.response_id || call.source_log_id)}</td>
    </tr>
  `).join("");
}

function renderPayload(call) {
  const title = document.getElementById("detailPayloadTitle");
  const request = document.getElementById("detailRequest");
  const response = document.getElementById("detailResponse");
  const event = document.getElementById("detailEvent");
  if (!call) {
    title.textContent = "Call details";
    request.textContent = "";
    response.textContent = "";
    event.textContent = "";
    renderRequestStats(null);
    setPayloadCopyAvailability(null);
    return;
  }
  title.textContent = `${call.model} · ${call.status} · ${number(call.total_tokens)} tokens`;
  request.textContent = pretty(call.request, emptyPayloadMessage("request", call));
  response.textContent = pretty(call.response, emptyPayloadMessage("response", call));
  event.textContent = pretty(call.event);
  renderRequestStats(call);
  setPayloadCopyAvailability(call);
}

function setPayloadCopyAvailability(call) {
  const values = {
    detailRequest: call?.request,
    detailResponse: call?.response,
    detailEvent: call?.event,
  };
  for (const [targetId, value] of Object.entries(values)) {
    const button = document.querySelector(`[data-copy-target="${targetId}"]`);
    if (!button) continue;
    const available = value != null && value !== "";
    button.disabled = !available;
    if (!available) {
      setCopyButtonBaseLabel(button, "Unavailable");
    } else if (button.dataset.copyLabel === "Unavailable") {
      setCopyButtonBaseLabel(button, "Copy");
    }
  }
}

async function writeClipboardText(text) {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text);
    return;
  }
  const input = document.createElement("textarea");
  input.value = text;
  input.setAttribute("readonly", "");
  input.style.position = "fixed";
  input.style.opacity = "0";
  document.body.appendChild(input);
  input.select();
  try {
    document.execCommand("copy");
  } finally {
    input.remove();
  }
}

function resetCopyButtons() {
  document.querySelectorAll(".payload-copy-button").forEach(button => {
    button.textContent = button.dataset.copyLabel || "Copy";
  });
}

function showCopyState(button, label) {
  button.textContent = label;
  const timerId = copyResetTimers.get(button);
  if (timerId) window.clearTimeout(timerId);
  copyResetTimers.set(button, window.setTimeout(() => {
    button.textContent = "Copy";
    copyResetTimers.delete(button);
  }, 1400));
}

async function copyPayload(button) {
  const targetId = button.dataset.copyTarget;
  const target = targetId ? document.getElementById(targetId) : null;
  if (!target) return;
  try {
    await writeClipboardText(target.textContent || "");
    showCopyState(button, "Copied");
  } catch (_error) {
    showCopyState(button, "Failed");
  }
}

function renderDetail() {
  const task = detail?.task;
  const calls = detail?.calls || [];
  renderMeta(task);
  renderCalls(calls);
  renderPayload(calls[selectedCall]);
}

function selectCall(index) {
  const calls = detail?.calls || [];
  if (index < 0 || index >= calls.length) return;
  selectedCall = index;
  renderDetail();
}

export async function openTaskDetail(threadId, turnId) {
  const dialog = document.getElementById("detailDialog");
  const error = document.getElementById("detailError");
  selectedCall = 0;
  detail = null;
  error.textContent = "";
  dialog.showModal();
  document.getElementById("detailMeta").innerHTML = "";
  document.getElementById("detailCalls").innerHTML = "";
  document.getElementById("detailRequest").textContent = "Loading...";
  document.getElementById("detailResponse").textContent = "";
  document.getElementById("detailEvent").textContent = "";

  try {
    const params = new URLSearchParams({ thread_id: threadId, turn_id: turnId });
    detail = await getJson(`/api/task-detail?${params.toString()}`);
    renderDetail();
  } catch (err) {
    error.textContent = err.message;
  }
}

export function initDetailModal() {
  const dialog = document.getElementById("detailDialog");
  document.getElementById("detailClose").addEventListener("click", () => dialog.close());
  resetCopyButtons();
  dialog.addEventListener("close", () => {
    detail = null;
    selectedCall = 0;
    resetCopyButtons();
    document.getElementById("detailMeta").innerHTML = "";
    document.getElementById("detailCalls").innerHTML = "";
    document.getElementById("detailRequest").textContent = "";
    document.getElementById("detailResponse").textContent = "";
    document.getElementById("detailEvent").textContent = "";
    document.getElementById("detailRequestStats").textContent = "";
  });
  document.getElementById("detailCalls").addEventListener("click", event => {
    const row = event.target.closest("[data-call-index]");
    if (row) selectCall(Number(row.dataset.callIndex));
  });
  document.getElementById("detailCalls").addEventListener("keydown", event => {
    if (event.key !== "Enter" && event.key !== " ") return;
    const row = event.target.closest("[data-call-index]");
    if (!row) return;
    event.preventDefault();
    selectCall(Number(row.dataset.callIndex));
  });
  dialog.addEventListener("click", event => {
    const button = event.target.closest(".payload-copy-button");
    if (button) copyPayload(button);
  });
}
