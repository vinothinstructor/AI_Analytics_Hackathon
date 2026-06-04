import { useModeStore } from "@/store/modeStore";

// Central fetch wrapper. Every API call in later phases goes through here so the
// current LLM mode is attached automatically as X-LLM-Mode. Paths are passed
// WITHOUT the /api prefix's backend form — we add /api here and the Vite proxy
// strips it (/api/health -> backend /health).
export async function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const mode = useModeStore.getState().mode;
  const headers = new Headers(init.headers);
  headers.set("X-LLM-Mode", mode);
  const url = path.startsWith("/api") ? path : `/api${path.startsWith("/") ? "" : "/"}${path}`;
  return fetch(url, { ...init, headers });
}
