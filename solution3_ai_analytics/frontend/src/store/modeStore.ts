import { create } from "zustand";

// The four LLM modes, selected via the ModeDropdown and sent on every API call
// as the X-LLM-Mode header (see lib/apiFetch.ts).
export type LlmMode = "MOCK" | "FAKE" | "CACHED" | "LIVE";

export const LLM_MODES: LlmMode[] = ["MOCK", "FAKE", "CACHED", "LIVE"];

// An explicit ?mode=… in the URL — wins over the server default and the stored
// value. Returns null if absent/invalid.
export function urlModeOverride(): LlmMode | null {
  if (typeof window === "undefined") return null;
  const m = new URLSearchParams(window.location.search).get("mode")?.toUpperCase() as
    | LlmMode
    | undefined;
  return m && LLM_MODES.includes(m) ? m : null;
}

// Synchronous initial mode: an explicit ?mode=… wins; otherwise FAKE as a safe
// placeholder until the app fetches the server's configured LLM_MODE (/health)
// and seeds the store from it (see OneHomeWrapper). ?recording=true only hides
// the dropdown (ModeDropdown.tsx) — it does NOT force a mode.
function initialMode(): LlmMode {
  return urlModeOverride() ?? "FAKE";
}

interface ModeState {
  mode: LlmMode;
  setMode: (mode: LlmMode) => void;
}

export const useModeStore = create<ModeState>((set) => ({
  mode: initialMode(),
  setMode: (mode) => set({ mode }),
}));
