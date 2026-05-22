const TABLE_WIDTHS_PREFIX = "token-lens:table-widths";
const TABLE_ORDER_PREFIX = "token-lens:table-order";
const TABLE_SCROLL_PREFIX = "token-lens:table-scroll";


function tableId(table) {
  return table.dataset.tableId || "table";
}


function storageKey(prefix, table) {
  return `${prefix}:${tableId(table)}`;
}


function readJson(key, fallback) {
  try {
    return JSON.parse(localStorage.getItem(key) || JSON.stringify(fallback));
  } catch {
    return fallback;
  }
}


export function readWidths(table) {
  return readJson(storageKey(TABLE_WIDTHS_PREFIX, table), {});
}


export function writeWidths(table, widths) {
  localStorage.setItem(storageKey(TABLE_WIDTHS_PREFIX, table), JSON.stringify(widths));
}


export function readOrder(table) {
  return readJson(storageKey(TABLE_ORDER_PREFIX, table), []);
}


export function writeOrder(table, order) {
  localStorage.setItem(storageKey(TABLE_ORDER_PREFIX, table), JSON.stringify(order));
}


export function readScroll(table) {
  const value = Number(localStorage.getItem(storageKey(TABLE_SCROLL_PREFIX, table)));
  return Number.isFinite(value) ? value : 0;
}


export function writeScroll(table, value) {
  localStorage.setItem(storageKey(TABLE_SCROLL_PREFIX, table), String(Math.max(0, Math.round(value || 0))));
}
