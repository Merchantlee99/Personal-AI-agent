const DEFAULT_PROXY_URL = "http://localhost:8000";

function parseTimeout(raw: string | undefined, fallbackMs: number) {
  const value = Number(raw || "");
  if (!Number.isFinite(value) || value <= 0) {
    return fallbackMs;
  }
  return value;
}

export function getProxyBaseUrl() {
  return process.env.LLM_PROXY_URL || DEFAULT_PROXY_URL;
}

export function buildProxyHeaders(): HeadersInit {
  const token = process.env.LLM_PROXY_INTERNAL_TOKEN?.trim() || "";
  return {
    "Content-Type": "application/json",
    ...(token ? { "x-internal-token": token } : {}),
  };
}

export async function fetchWithTimeout(
  input: string,
  init: RequestInit = {},
  fallbackTimeoutMs = 15000
) {
  const timeoutMs = parseTimeout(process.env.LLM_PROXY_TIMEOUT_MS, fallbackTimeoutMs);
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(input, { ...init, signal: controller.signal });
  } finally {
    clearTimeout(timer);
  }
}
