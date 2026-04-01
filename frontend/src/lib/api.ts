/** Build absolute URL for API paths like /health, /compile (inner routes, no /api prefix). */
function apiUrl(path: string): string {
  const normalized = path.startsWith("/") ? path : `/${path}`;
  const custom = (import.meta.env.VITE_API_URL as string | undefined)?.replace(
    /\/$/,
    ""
  );
  if (custom) {
    return `${custom}${normalized}`;
  }
  if (import.meta.env.DEV) {
    return `http://127.0.0.1:8000${normalized}`;
  }
  // Production on Vercel: FastAPI mounted at /api
  return `/api${normalized}`;
}

/** Backward-compatible base (origin only) for status bar / display. */
export function getApiBase(): string {
  const custom = (import.meta.env.VITE_API_URL as string | undefined)?.replace(
    /\/$/,
    ""
  );
  if (custom) return custom;
  if (import.meta.env.DEV) return "http://127.0.0.1:8000";
  if (typeof window !== "undefined") {
    return window.location.origin;
  }
  return "";
}

export type ApiEnvelope = {
  success: boolean;
  message: string;
  input: Record<string, unknown>;
  output: Record<string, unknown>;
};

export async function fetchHealth(): Promise<{ ok: boolean; version?: string }> {
  const res = await fetch(apiUrl("/health"), { method: "GET" });
  if (!res.ok) throw new Error(`Health check failed (${res.status})`);
  return res.json() as Promise<{ ok: boolean; version?: string }>;
}

export async function postCode(
  path: "/compile" | "/run" | "/ai-suggest",
  code: string
): Promise<ApiEnvelope> {
  const res = await fetch(apiUrl(path), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code }),
  });
  const text = await res.text();
  let body: ApiEnvelope;
  try {
    body = JSON.parse(text) as ApiEnvelope;
  } catch {
    throw new Error(text || `HTTP ${res.status}`);
  }
  if (!res.ok) {
    throw new Error(body.message || `HTTP ${res.status}`);
  }
  return body;
}
