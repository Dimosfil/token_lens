const TAB_SETTINGS_KEY = "token-lens:active-tab:v1";
const DEFAULT_TAB = "codex";


function tabExists(tabName) {
  return Array.from(document.querySelectorAll("[data-tab-panel]"))
    .some(panel => panel.dataset.tabPanel.split(/\s+/).includes(tabName));
}


function readActiveTab() {
  const stored = localStorage.getItem(TAB_SETTINGS_KEY);
  return stored && tabExists(stored) ? stored : DEFAULT_TAB;
}


export function setActiveTab(tabName) {
  const nextTab = tabExists(tabName) ? tabName : DEFAULT_TAB;
  document.querySelectorAll("[data-tab-panel]").forEach(panel => {
    panel.hidden = !panel.dataset.tabPanel.split(/\s+/).includes(nextTab);
  });
  document.querySelectorAll("[data-tab-target]").forEach(button => {
    const isActive = button.dataset.tabTarget === nextTab;
    button.classList.toggle("is-active", isActive);
    button.setAttribute("aria-selected", String(isActive));
  });
  localStorage.setItem(TAB_SETTINGS_KEY, nextTab);
  document.dispatchEvent(new CustomEvent("token-lens:tab-change", { detail: { tab: nextTab } }));
}


export function initTabs() {
  document.querySelector(".workspace-tabs")?.addEventListener("click", event => {
    const button = event.target.closest("[data-tab-target]");
    if (!button) return;
    setActiveTab(button.dataset.tabTarget);
  });
  setActiveTab(readActiveTab());
}
