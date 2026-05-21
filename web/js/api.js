let activeRequests = 0;

export function hasActiveRequests() {
  return activeRequests > 0;
}

export async function getJson(url, options = {}, timeoutMs = 30000) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  activeRequests += 1;

  try {
    const res = await fetch(url, {
      cache: "no-store",
      ...options,
      signal: controller.signal,
    });
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
    return res.json();
  } catch (err) {
    if (err.name === "AbortError") {
      throw new Error(`Request timed out after ${Math.round(timeoutMs / 1000)}s`);
    }
    throw err;
  } finally {
    activeRequests = Math.max(0, activeRequests - 1);
    clearTimeout(timeout);
  }
}
