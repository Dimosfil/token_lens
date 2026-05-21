const fmt = new Intl.NumberFormat("ru-RU");

export function number(value) {
  return fmt.format(value || 0);
}

export function time(value) {
  if (!value) return "";
  return new Date(value).toLocaleString("ru-RU");
}

export function duration(seconds) {
  const totalSeconds = Math.max(0, Number(seconds || 0));
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const remainingSeconds = Math.floor(totalSeconds % 60);
  if (hours > 0) {
    return `${hours}:${String(minutes).padStart(2, "0")}:${String(remainingSeconds).padStart(2, "0")}`;
  }
  return `${minutes}:${String(remainingSeconds).padStart(2, "0")}`;
}
