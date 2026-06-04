import { create } from "zustand";

// The four LLM modes, selected via the ModeDropdown and sent on every API call
// as the X-LLM-Mode header (see lib/apiFetch.ts).
export type LlmMode = "MOCK" | "FAKE" | "CACHED" | "LIVE";

export const LLM_MODES: LlmMode[] = ["MOCK", "FAKE", "CACHED", "LIVE"];

// Initial mode. Defaults to FAKE (no Azure needed); an explicit ?mode=… overrides.
// ?recording=true only hides the ModeDropdown (see ModeDropdown.tsx) — it does NOT
// force a mode, so recording uses whatever you've selected. For the office-laptop
// recording, pass ?recording=true&mode=CACHED (or &mode=LIVE) explicitly.
function initialMode(): LlmMode {
  if (typeof window === "undefined") return "FAKE";
  const override = new URLSearchParams(window.location.search).get("mode")?.toUpperCase() as
    | LlmMode
    | undefined;
  return override && LLM_MODES.includes(override) ? override : "FAKE";
}

interface ModeState {
  mode: LlmMode;
  setMode: (mode: LlmMode) => void;
}

export const useModeStore = create<ModeState>((set) => ({
  mode: initialMode(),
  setMode: (mode) => set({ mode }),
}));
