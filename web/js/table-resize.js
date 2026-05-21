const MIN_COLUMN_WIDTH = 56;
const DEFAULT_COLUMN_WIDTH = 120;

function tableKey(table) {
  return `token-lens:table-widths:${table.dataset.tableId || "table"}`;
}

function readWidths(table) {
  try {
    return JSON.parse(localStorage.getItem(tableKey(table)) || "[]");
  } catch {
    return [];
  }
}

function writeWidths(table, widths) {
  localStorage.setItem(tableKey(table), JSON.stringify(widths));
}

function columnWidth(th) {
  return Math.max(th.getBoundingClientRect().width, MIN_COLUMN_WIDTH);
}

function applyColumnWidth(table, columnIndex, width) {
  const safeWidth = Math.max(Math.round(width), MIN_COLUMN_WIDTH);
  table.querySelectorAll(`tr > *:nth-child(${columnIndex + 1})`).forEach(cell => {
    cell.style.width = `${safeWidth}px`;
    cell.style.minWidth = `${safeWidth}px`;
  });
  syncTableWidth(table);
  return safeWidth;
}

function syncTableWidth(table) {
  const widths = Array.from(table.querySelectorAll("thead th"))
    .map(th => Math.max(Math.round(th.getBoundingClientRect().width), MIN_COLUMN_WIDTH));
  const totalWidth = widths.reduce((sum, width) => sum + width, 0);
  if (totalWidth > 0) {
    table.style.width = `${totalWidth}px`;
    table.style.minWidth = `max(100%, ${totalWidth}px)`;
    syncTopScrollbarWidth(table, totalWidth);
  }
}

function topScrollbar(table) {
  const wrap = table.closest(".table-wrap");
  const sibling = wrap?.previousElementSibling;
  return sibling?.classList.contains("table-scroll-top") ? sibling : null;
}

function syncTopScrollbarWidth(table, width) {
  const top = topScrollbar(table);
  const spacer = top?.querySelector(".table-scroll-spacer");
  if (spacer) spacer.style.width = `${width}px`;
}

function ensureTopScrollbar(table) {
  const wrap = table.closest(".table-wrap");
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
    syncing = false;
  });
  wrap.addEventListener("scroll", () => {
    if (syncing) return;
    syncing = true;
    top.scrollLeft = wrap.scrollLeft;
    syncing = false;
  });
}

function saveColumnWidth(table, columnIndex, width) {
  const widths = readWidths(table);
  widths[columnIndex] = width;
  writeWidths(table, widths);
}

function restoreWidths(table) {
  readWidths(table).forEach((width, index) => {
    if (Number.isFinite(width)) applyColumnWidth(table, index, width);
  });
  syncTableWidth(table);
}

function startResize(event, table, th, columnIndex) {
  event.preventDefault();
  const startX = event.clientX;
  const startWidth = columnWidth(th);
  document.body.classList.add("is-resizing-table");

  function onMove(moveEvent) {
    const nextWidth = startWidth + moveEvent.clientX - startX;
    applyColumnWidth(table, columnIndex, nextWidth);
  }

  function onUp() {
    document.removeEventListener("pointermove", onMove);
    document.removeEventListener("pointerup", onUp);
    document.body.classList.remove("is-resizing-table");
    saveColumnWidth(table, columnIndex, columnWidth(th));
    syncTableWidth(table);
  }

  document.addEventListener("pointermove", onMove);
  document.addEventListener("pointerup", onUp, { once: true });
}

function addResizeHandles(table) {
  ensureTopScrollbar(table);
  table.querySelectorAll("thead th").forEach((th, index) => {
    if (!th.style.width) {
      applyColumnWidth(table, index, Math.max(columnWidth(th), DEFAULT_COLUMN_WIDTH));
    }
    const handle = document.createElement("span");
    handle.className = "col-resizer";
    handle.setAttribute("role", "separator");
    handle.setAttribute("aria-orientation", "vertical");
    handle.title = "Изменить ширину столбца";
    handle.addEventListener("pointerdown", event => startResize(event, table, th, index));
    th.appendChild(handle);
  });
  syncTableWidth(table);
}

export function initResizableTables() {
  document.querySelectorAll("table[data-resizable]").forEach(table => {
    if (table.dataset.resizeReady) return;
    table.dataset.resizeReady = "true";
    addResizeHandles(table);
    restoreWidths(table);
  });
}
