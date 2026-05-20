export function setAutoStatus(message, isError = false) {
  const el = document.getElementById("autoStatus");
  if (!el) return;
  el.textContent = message;
  el.classList.toggle("is-error", isError);
}
