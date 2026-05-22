function slug(value, fallback) {
  const text = String(value || "")
    .trim()
    .toLowerCase()
    .replace(/\s+/g, "-")
    .replace(/[^a-z0-9_-]/g, "");
  return text || fallback;
}


export function setupColumnKeys(table) {
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


export function columnKeys(table) {
  return table.__columnKeys || setupColumnKeys(table);
}


export function currentOrder(table) {
  return Array.from(table.querySelectorAll("thead th")).map(th => th.dataset.columnKey);
}


export function completeOrder(table, order) {
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


export function labelCells(table) {
  const keys = columnKeys(table);
  table.querySelectorAll("tbody tr").forEach(row => {
    Array.from(row.children).forEach((cell, index) => {
      if (!cell.dataset.columnKey) cell.dataset.columnKey = keys[index] || `column-${index}`;
    });
  });
}


export function reorderChildren(parent, selector, order) {
  const children = Array.from(parent.querySelectorAll(selector));
  const visibleOrder = children.map(child => child.dataset.columnKey);
  if (order.every((key, index) => visibleOrder[index] === key)) return;

  const byKey = new Map(children.map(child => [child.dataset.columnKey, child]));
  order.forEach(key => {
    const child = byKey.get(key);
    if (child) parent.appendChild(child);
  });
}
