import { getJson } from "./api.js";
import { number, time } from "./format.js";
import { escapeHtml } from "./render/html.js";

let detail = null;
let selectedCall = 0;

function pretty(value) {
  if (value == null || value === "") return "No captured payload";
  if (typeof value === "string") return value;
  return JSON.stringify(value, null, 2);
}

function joinList(value) {
  if (Array.isArray(value)) return value.join(", ");
  return value || "";
}

function metric(label, value) {
  return `<div class="detail-metric"><span>${label}</span><strong>${escapeHtml(value)}</strong></div>`;
}

function rawEventLabel(captured) {
  return captured ? "Captured" : "Missing";
}

function renderMeta(task) {
  const el = document.getElementById("detailMeta");
  if (!task) {
    el.innerHTML = "";
    return;
  }
  el.innerHTML = [
    metric("Start", time(task.started_at)),
    metric("Finish", time(task.finished_at)),
    metric("Calls", number(task.model_calls)),
    metric("Total tokens", number(task.total_tokens)),
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
      <td>${number(call.input_tokens)}</td>
      <td>${number(call.cached_input_tokens)}</td>
      <td>${number(call.output_tokens)}</td>
      <td>${number(call.reasoning_output_tokens)}</td>
      <td><span class="raw-event raw-event-${call.raw_event_captured ? "captured" : "missing"}">${rawEventLabel(call.raw_event_captured)}</span></td>
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
    return;
  }
  title.textContent = `${call.model} · ${call.status} · ${number(call.total_tokens)} tokens`;
  request.textContent = pretty(call.request);
  response.textContent = pretty(call.response);
  event.textContent = pretty(call.event);
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
  dialog.addEventListener("close", () => {
    detail = null;
    selectedCall = 0;
    document.getElementById("detailMeta").innerHTML = "";
    document.getElementById("detailCalls").innerHTML = "";
    document.getElementById("detailRequest").textContent = "";
    document.getElementById("detailResponse").textContent = "";
    document.getElementById("detailEvent").textContent = "";
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
}
