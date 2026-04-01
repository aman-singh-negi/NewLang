/** Backend base URL; Vite injects import.meta.env.VITE_API_URL. */
export function getApiBase(): string {
  return (import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000").replace(
    /\/$/,
    ""
  );
}

export type ApiEnvelope = {
  success: boolean;
  message: string;
  input: Record<string, unknown>;
  output: Record<string, unknown>;
};

export async function fetchHealth(): Promise<{ ok: boolean; version?: string }> {
  const res = await fetch(`${getApiBase()}/health`, { method: "GET" });
  if (!res.ok) throw new Error(`Health check failed (${res.status})`);
  return res.json() as Promise<{ ok: boolean; version?: string }>;
}

export async function postCode(
  path: "/compile" | "/run" | "/ai-suggest",
  code: string
): Promise<ApiEnvelope> {
  const res = await fetch(`${getApiBase()}${path}`, {
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
