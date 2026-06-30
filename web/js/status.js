export function setAutoStatus(message, isError = false, connectionState = "online") {
  const el = document.getElementById("autoStatus");
  if (!el) return;
  const stateLabel = connectionState === "offline"
    ? "Backend offline"
    : connectionState === "busy"
      ? "Backend busy"
      : "Backend online";
  el.textContent = `${stateLabel} · ${message}`;
  el.classList.toggle("is-error", isError);
  el.classList.toggle("is-online", connectionState === "online" && !isError);
  el.classList.toggle("is-busy", connectionState === "busy" && !isError);
  el.classList.toggle("is-offline", connectionState === "offline" || isError);
}
