const MIN_COLUMN_WIDTH = 56;
const DEFAULT_COLUMN_WIDTH = 120;

function tableId(table) {
  return table.dataset.tableId || "table";
}

function tableKey(table) {
  return `token-lens:table-widths:${tableId(table)}`;
}

function orderKey(table) {
  return `token-lens:table-order:${tableId(table)}`;
}

function scrollKey(table) {
  return `token-lens:table-scroll:${tableId(table)}`;
}

function readJson(key, fallback) {
  try {
    return JSON.parse(localStorage.getItem(key) || JSON.stringify(fallback));
  } catch {
    return fallback;
  }
}

function readWidths(table) {
  return readJson(tableKey(table), {});
}

function writeWidths(table, widths) {
  localStorage.setItem(tableKey(table), JSON.stringify(widths));
}

function readOrder(table) {
  return readJson(orderKey(table), []);
}

function writeOrder(table, order) {
  localStorage.setItem(orderKey(table), JSON.stringify(order));
}

function readScroll(table) {
  const value = Number(localStorage.getItem(scrollKey(table)));
  return Number.isFinite(value) ? value : 0;
}

function writeScroll(table, value) {
  localStorage.setItem(scrollKey(table), String(Math.max(0, Math.round(value || 0))));
}

function slug(value, fallback) {
  const text = String(value || "")
    .trim()
    .toLowerCase()
    .replace(/\s+/g, "-")
    .replace(/[^a-z0-9_-]/g, "");
  return text || fallback;
}

function setupColumnKeys(table) {
  if (table.__columnKeys) return table.__columnKeys;
  const keys = Array.from(table.querySelectorAll("thead th")).map((th, index) => {
    const key = th.dataset.columnKey || slug(th.textContent, `column-${index}`);
    th.dataset.columnKey = key;
    th.dataset.originalIndex = String(index);
    return key;
  });
  table.__columnKeys = keys;
  return keys;
}

function columnKeys(table) {
  return table.__columnKeys || setupColumnKeys(table);
}

function currentOrder(table) {
  return Array.from(table.querySelectorAll("thead th")).map(th => th.dataset.columnKey);
}

function completeOrder(table, order) {
  const keys = columnKeys(table);
  const seen = new Set();
  const safe = [];
  order.forEach(key => {
    if (keys.includes(key) && !seen.has(key)) {
      seen.add(key);
      safe.push(key);
    }
  });
  keys.forEach(key => {
    if (!seen.has(key)) safe.push(key);
  });
  return safe;
}

function labelCells(table) {
  const keys = columnKeys(table);
  table.querySelectorAll("tbody tr").forEach(row => {
    Array.from(row.children).forEach((cell, index) => {
      if (!cell.dataset.columnKey) cell.dataset.columnKey = keys[index] || `column-${index}`;
    });
  });
}

function reorderChildren(parent, selector, order) {
  const children = Array.from(parent.querySelectorAll(selector));
  const visibleOrder = children.map(child => child.dataset.columnKey);
  if (order.every((key, index) => visibleOrder[index] === key)) return;

  const byKey = new Map(children.map(child => [child.dataset.columnKey, child]));
  order.forEach(key => {
    const child = byKey.get(key);
    if (child) parent.appendChild(child);
  });
}

function applyColumnOrder(table, order = readOrder(table)) {
  if (!table.dataset.reorderable) return;
  const safeOrder = completeOrder(table, order);
  const headRow = table.querySelector("thead tr");
  if (!headRow) return;

  labelCells(table);
  reorderChildren(headRow, "th", safeOrder);
  table.querySelectorAll("tbody tr").forEach(row => reorderChildren(row, ":scope > *", safeOrder));
  syncTableWidth(table);
}

function columnWidth(th) {
  const styleWidth = Number.parseFloat(th.style.width);
  const width = Number.isFinite(styleWidth) ? styleWidth : th.getBoundingClientRect().width;
  return Math.max(width, MIN_COLUMN_WIDTH);
}

function applyColumnWidthByKey(table, key, width) {
  const safeWidth = Math.max(Math.round(width), MIN_COLUMN_WIDTH);
  table.querySelectorAll("tr").forEach(row => {
    const cell = Array.from(row.children).find(item => item.dataset.columnKey === key);
    if (!cell) return;
    cell.style.width = `${safeWidth}px`;
    cell.style.minWidth = `${safeWidth}px`;
    cell.style.maxWidth = `${safeWidth}px`;
  });
  syncTableWidth(table);
  return safeWidth;
}

function applyColumnWidth(table, columnIndex, width) {
  const key = currentOrder(table)[columnIndex];
  if (!key) return null;
  return applyColumnWidthByKey(table, key, width);
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

function tableWrap(table) {
  return table.closest(".table-wrap");
}

function syncTopScrollbarWidth(table, width) {
  const top = topScrollbar(table);
  const spacer = top?.querySelector(".table-scroll-spacer");
  if (spacer) spacer.style.width = `${width}px`;
}

function restoreScroll(table) {
  const wrap = tableWrap(table);
  const top = topScrollbar(table);
  const left = readScroll(table);
  if (wrap) wrap.scrollLeft = left;
  if (top) top.scrollLeft = left;
}

function ensureTopScrollbar(table) {
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

function saveWidthsSnapshot(table) {
  const widths = {};
  table.querySelectorAll("thead th").forEach(th => {
    if (th.dataset.columnKey) widths[th.dataset.columnKey] = Math.round(columnWidth(th));
  });
  writeWidths(table, widths);
}

function saveColumnWidth(table, key, width) {
  if (!key) return;
  const widths = readWidths(table);
  widths[key] = width;
  writeWidths(table, widths);
}

function restoreWidths(table) {
  const widths = readWidths(table);
  const legacyWidths = Array.isArray(widths) ? widths : null;
  currentOrder(table).forEach((key, index) => {
    const canonicalIndex = columnKeys(table).indexOf(key);
    const width = legacyWidths ? legacyWidths[canonicalIndex] : widths[key];
    if (Number.isFinite(width)) applyColumnWidthByKey(table, key, width);
  });
  syncTableWidth(table);
  restoreScroll(table);
}

function startResize(event, table, th) {
  event.stopPropagation();
  event.preventDefault();
  const key = th.dataset.columnKey;
  if (!key) return;
  const startX = event.clientX;
  const startWidth = columnWidth(th);
  event.currentTarget.setPointerCapture?.(event.pointerId);
  document.body.classList.add("is-resizing-table");

  function onMove(moveEvent) {
    const nextWidth = startWidth + moveEvent.clientX - startX;
    applyColumnWidthByKey(table, key, nextWidth);
    saveWidthsSnapshot(table);
  }

  function onUp() {
    document.removeEventListener("pointermove", onMove);
    document.removeEventListener("pointerup", onUp);
    document.body.classList.remove("is-resizing-table");
    saveColumnWidth(table, key, columnWidth(th));
    saveWidthsSnapshot(table);
    syncTableWidth(table);
    restoreScroll(table);
  }

  document.addEventListener("pointermove", onMove);
  document.addEventListener("pointerup", onUp, { once: true });
}

function moveColumn(table, fromKey, toKey) {
  if (!fromKey || !toKey || fromKey === toKey) return;
  const order = currentOrder(table);
  const fromIndex = order.indexOf(fromKey);
  const toIndex = order.indexOf(toKey);
  if (fromIndex < 0 || toIndex < 0) return;
  order.splice(fromIndex, 1);
  order.splice(toIndex, 0, fromKey);
  writeOrder(table, order);
  applyColumnOrder(table, order);
  restoreWidths(table);
  saveWidthsSnapshot(table);
}

function addColumnDrag(table) {
  setupColumnKeys(table);
  table.querySelectorAll("thead th").forEach(th => {
    th.draggable = true;
    th.title = th.title || "Drag to reorder";
    th.addEventListener("dragstart", event => {
      table.dataset.dragColumnKey = th.dataset.columnKey;
      event.dataTransfer.effectAllowed = "move";
      event.dataTransfer.setData("text/plain", th.dataset.columnKey);
      th.classList.add("is-dragging-column");
    });
    th.addEventListener("dragend", () => {
      table.querySelectorAll("thead th").forEach(item => item.classList.remove("is-dragging-column", "is-drag-over"));
      delete table.dataset.dragColumnKey;
    });
    th.addEventListener("dragover", event => {
      if (!table.dataset.dragColumnKey) return;
      event.preventDefault();
      event.dataTransfer.dropEffect = "move";
      th.classList.add("is-drag-over");
    });
    th.addEventListener("dragleave", () => th.classList.remove("is-drag-over"));
    th.addEventListener("drop", event => {
      event.preventDefault();
      th.classList.remove("is-drag-over");
      const fromKey = event.dataTransfer.getData("text/plain") || table.dataset.dragColumnKey;
      moveColumn(table, fromKey, th.dataset.columnKey);
    });
  });
  applyColumnOrder(table);
}

function addResizeHandles(table) {
  ensureTopScrollbar(table);
  setupColumnKeys(table);
  if (table.dataset.reorderable) addColumnDrag(table);
  table.querySelectorAll("thead th").forEach((th, index) => {
    if (!th.style.width) {
      applyColumnWidth(table, index, Math.max(columnWidth(th), DEFAULT_COLUMN_WIDTH));
    }
    const handle = document.createElement("span");
    handle.className = "col-resizer";
    handle.setAttribute("role", "separator");
    handle.setAttribute("aria-orientation", "vertical");
    handle.title = "Resize column";
    handle.draggable = false;
    handle.addEventListener("dragstart", event => event.preventDefault());
    handle.addEventListener("pointerdown", event => startResize(event, table, th));
    th.appendChild(handle);
  });
  syncTableWidth(table);
  restoreScroll(table);
}

function observeRows(table) {
  const tbody = table.querySelector("tbody");
  if (!tbody) return;
  const observer = new MutationObserver(() => {
    applyColumnOrder(table);
    restoreWidths(table);
  });
  observer.observe(tbody, { childList: true });
}

export function initResizableTables() {
  document.querySelectorAll("table[data-resizable]").forEach(table => {
    if (table.dataset.resizeReady) {
      applyColumnOrder(table);
      restoreWidths(table);
      return;
    }
    table.dataset.resizeReady = "true";
    addResizeHandles(table);
    restoreWidths(table);
    observeRows(table);
  });
}
