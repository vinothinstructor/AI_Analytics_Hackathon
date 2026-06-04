import { useEffect, useRef, useState } from "react";
import { Check, ChevronDown } from "lucide-react";

import { LLM_MODES, useModeStore, type LlmMode } from "@/store/modeStore";
import { cn } from "@/lib/utils";

// Hidden when the URL carries ?recording=true (clean demo capture).
function isRecording(): boolean {
  return new URLSearchParams(window.location.search).get("recording") === "true";
}

const MODE_META: Record<LlmMode, { dot: string; hint: string }> = {
  MOCK: { dot: "bg-slate-400", hint: "Skeleton responses" },
  FAKE: { dot: "bg-teal-400", hint: "Local · no Azure" },
  CACHED: { dot: "bg-amber-400", hint: "Replay captured" },
  LIVE: { dot: "bg-green-400", hint: "Real-time Azure" },
};

export function ModeDropdown() {
  const mode = useModeStore((s) => s.mode);
  const setMode = useModeStore((s) => s.setMode);
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", onClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  if (isRecording()) return null;

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-2 rounded-lg border border-white/15 bg-navy-800 px-3 py-1.5 text-xs transition hover:border-white/30"
        aria-haspopup="listbox"
        aria-expanded={open}
      >
        <span className="font-medium uppercase tracking-wide text-slate-400">LLM</span>
        <span className={cn("h-2 w-2 rounded-full", MODE_META[mode].dot)} />
        <span className="font-semibold text-white">{mode}</span>
        <ChevronDown className={cn("h-3.5 w-3.5 text-slate-400 transition-transform", open && "rotate-180")} />
      </button>

      {open && (
        <ul
          role="listbox"
          className="absolute right-0 z-[60] mt-1.5 w-56 overflow-hidden rounded-xl border border-slate-200 bg-white p-1 shadow-xl"
        >
          {LLM_MODES.map((m) => {
            const active = m === mode;
            return (
              <li key={m}>
                <button
                  role="option"
                  aria-selected={active}
                  onClick={() => {
                    setMode(m);
                    setOpen(false);
                  }}
                  className={cn(
                    "flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-left transition",
                    active ? "bg-teal-50" : "hover:bg-slate-50",
                  )}
                >
                  <span className={cn("h-2 w-2 shrink-0 rounded-full", MODE_META[m].dot)} />
                  <span className="flex-1">
                    <span className="block text-sm font-semibold text-navy">{m}</span>
                    <span className="block text-[11px] text-slate-400">{MODE_META[m].hint}</span>
                  </span>
                  {active && <Check className="h-4 w-4 shrink-0 text-teal-600" />}
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
