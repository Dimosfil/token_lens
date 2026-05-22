import { readScroll, writeScroll } from "./table-storage.js";


export function topScrollbar(table) {
  const wrap = tableWrap(table);
  const sibling = wrap?.previousElementSibling;
  return sibling?.classList.contains("table-scroll-top") ? sibling : null;
}


export function tableWrap(table) {
  return table.closest(".table-wrap");
}


export function syncTopScrollbarWidth(table, width) {
  const top = topScrollbar(table);
  const spacer = top?.querySelector(".table-scroll-spacer");
  if (spacer) spacer.style.width = `${width}px`;
}


export function restoreScroll(table) {
  const wrap = tableWrap(table);
  const top = topScrollbar(table);
  const left = readScroll(table);
  if (wrap) wrap.scrollLeft = left;
  if (top) top.scrollLeft = left;
}


export function ensureTopScrollbar(table) {
  const wrap = tableWrap(table);
  if (!wrap) return;

  let top = topScrollbar(table);
  if (!top) {
    top = document.createElement("div");
    top.className = "table-scroll-top";
    top.setAttribute("aria-hidden", "true");

    const spacer = document.createElement("div");
    spacer.className = "table-scroll-spacer";
    top.appendChild(spacer);
    wrap.parentElement.insertBefore(top, wrap);
  }

  let syncing = false;
  top.addEventListener("scroll", () => {
    if (syncing) return;
    syncing = true;
    wrap.scrollLeft = top.scrollLeft;
    writeScroll(table, top.scrollLeft);
    syncing = false;
  });
  wrap.addEventListener("scroll", () => {
    if (syncing) return;
    syncing = true;
    top.scrollLeft = wrap.scrollLeft;
    writeScroll(table, wrap.scrollLeft);
    syncing = false;
  });
}
