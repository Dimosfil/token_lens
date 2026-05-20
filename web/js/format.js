const fmt = new Intl.NumberFormat("ru-RU");

export function number(value) {
  return fmt.format(value || 0);
}

export function time(value) {
  if (!value) return "";
  return new Date(value).toLocaleString("ru-RU");
}
