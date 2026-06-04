import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { Check, ChevronDown, ChevronUp, Loader2 } from "lucide-react";

import { STAGE_LABELS, STAGE_ORDER, StageName, StageState } from "@/lib/types";
import { cn } from "@/lib/utils";

// Single tunable constant — minimum visible dwell per stage so the pipeline is
// perceptible even when the backend (FAKE/CACHED) answers in ~2 ms. Tune here for
// the recording. In LIVE a stage stays "running" until its real `done` arrives
// (we only advance once BOTH the dwell has elapsed AND the backend reports done).
export const STAGE_DWELL_MS = 400;

interface Props {
  stages: Record<StageName, StageState>;
  pipelineDone: boolean;
  latencyMs?: number | null;
  onComplete: () => void;
  instant?: boolean; // already revealed -> render collapsed final state, no animation
}

export function AgentReasoning({ stages, latencyMs, onComplete, instant = false }: Props) {
  // How many stages have visually completed (0..5). The stage at `visualIndex`
  // is the one currently "reasoning". When `instant`, start fully complete.
  const [visualIndex, setVisualIndex] = useState(instant ? STAGE_ORDER.length : 0);
  const [userExpanded, setUserExpanded] = useState(false);
  const fired = useRef(false);

  // Advance one stage at a time: wait for the backend to finish this stage, then
  // hold it for the min dwell before moving on. Skipped entirely when `instant`.
  useEffect(() => {
    if (instant || visualIndex >= STAGE_ORDER.length) return;
    const backendDone = stages[STAGE_ORDER[visualIndex]].status === "done";
    if (!backendDone) return; // wait for the real `done` (re-runs when stages change)
    const t = setTimeout(() => setVisualIndex((i) => i + 1), STAGE_DWELL_MS);
    return () => clearTimeout(t);
  }, [instant, visualIndex, stages]);

  const complete = visualIndex >= STAGE_ORDER.length;
  useEffect(() => {
    if (complete && !fired.current) {
      fired.current = true;
      onComplete();
    }
  }, [complete, onComplete]);

  // Collapsed summary line (after completion, unless the user re-expanded).
  if (complete && !userExpanded) {
    return (
      <button
        onClick={() => setUserExpanded(true)}
        className="mb-2 flex items-center gap-1.5 text-xs text-slate-400 transition hover:text-slate-600"
      >
        <Check className="h-3.5 w-3.5 text-teal-600" />✓ 5 stages
        {typeof latencyMs === "number" ? ` · ${latencyMs}ms` : ""}
        <ChevronDown className="h-3 w-3" />
      </button>
    );
  }

  return (
    <div className="mb-3 rounded-lg border border-slate-100 bg-white/60 p-2">
      {STAGE_ORDER.map((s, i) => {
        const state: "done" | "running" | "pending" =
          i < visualIndex ? "done" : i === visualIndex ? "running" : "pending";
        const detail = stages[s].detail;
        return (
          <div key={s} className="flex items-start gap-2 px-1 py-1">
            <span className="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center">
              {state === "running" && <Loader2 className="h-3.5 w-3.5 animate-spin text-teal-500" />}
              {state === "done" && <Check className="h-3.5 w-3.5 text-teal-600" />}
              {state === "pending" && <span className="h-1.5 w-1.5 rounded-full bg-slate-300" />}
            </span>
            <div className="min-w-0">
              <div
                className={cn(
                  "text-xs font-medium",
                  state === "running" && "text-teal-700",
                  state === "done" && "text-slate-500",
                  state === "pending" && "text-slate-300",
                )}
              >
                {STAGE_LABELS[s]}
              </div>
              {detail && state !== "pending" && (
                <motion.div
                  initial={{ opacity: 0, y: -2 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="text-[11px] leading-snug text-slate-400"
                >
                  {detail}
                </motion.div>
              )}
            </div>
          </div>
        );
      })}
      {complete && userExpanded && (
        <button
          onClick={() => setUserExpanded(false)}
          className="mt-1 flex items-center gap-1 px-1 text-[11px] text-slate-400 hover:text-slate-600"
        >
          <ChevronUp className="h-3 w-3" /> Hide steps
        </button>
      )}
    </div>
  );
}
