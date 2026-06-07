import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { AlertCircle, Code2, Sparkles } from "lucide-react";

import { AIMessageT } from "@/lib/types";
import { AgentReasoning } from "./AgentReasoning";
import { ChartRenderer } from "./ChartRenderer";
import { FollowUpChips } from "./FollowUpChips";
import { StreamingText } from "./StreamingText";

interface Props {
  message: AIMessageT;
  onPickFollowup: (q: string) => void;
  onShowSql: (id: string) => void;
  onRevealed: (id: string) => void;
  streaming: boolean;
}

// Reveal rhythm (first arrival only): agent-reasoning sequence → summary types →
// chart fades → chips. Once `message.revealed` is set, the message renders in its
// final state instantly (no replay) on any later re-mount (panel close/reopen).
export function AIResponse({ message, onPickFollowup, onShowSql, onRevealed, streaming }: Props) {
  const m = message;
  const instant = m.revealed;
  const [reasoningComplete, setReasoningComplete] = useState(false);
  const [textComplete, setTextComplete] = useState(false);

  // Show the agent-reasoning indicator the instant the message exists — before the
  // backend's first stage event arrives (the 1–2 s Azure gap in LIVE). With the
  // default empty stages, its first step ("Retrieving schema") renders in its
  // running/spinner state right away, so the bubble is never empty. Real stage
  // events then flow into the SAME mounted component (no remount, no flicker).
  // `awaitingContent` covers the pre-stage gap and any no-stage fast path until
  // the first token/error lands; once content arrives the indicator yields to it.
  const awaitingContent = !instant && !m.error && !m.done && m.summary.length === 0;
  const showReasoning = instant ? m.hasStages : m.hasStages || awaitingContent;

  // Summary streams only after the reasoning indicator completes; with no reasoning
  // shown (fast path, content already in) it shows immediately. When `instant`,
  // everything shows at once.
  const summaryReady = instant || (showReasoning ? reasoningComplete : true);
  const revealChart = instant || textComplete;

  // Persist completion once the first-arrival animation finishes, so re-mounts
  // are static. (No-op when already instant.)
  useEffect(() => {
    if (!instant && m.done && textComplete) onRevealed(m.id);
  }, [instant, m.done, textComplete, m.id, onRevealed]);

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="flex gap-2">
      <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-navy text-teal-400">
        <Sparkles className="h-4 w-4" />
      </div>
      <div className="min-w-0 flex-1">
        <div className="mb-1 text-[11px] font-medium text-slate-400">IQVIA AI · just now</div>
        <div className="rounded-2xl rounded-tl-sm border border-slate-200 bg-slate-50 px-3.5 py-2.5">
          {m.error ? (
            <div className="flex items-start gap-2 text-sm text-red-600">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
              <span>{m.error}</span>
            </div>
          ) : (
            <>
              {showReasoning && (
                <AgentReasoning
                  stages={m.stages}
                  pipelineDone={m.done}
                  latencyMs={m.trust?.audit.latency_ms}
                  instant={instant}
                  onComplete={() => setReasoningComplete(true)}
                />
              )}
              {summaryReady && (
                <StreamingText
                  text={m.summary}
                  done={m.done}
                  instant={instant}
                  onComplete={() => setTextComplete(true)}
                />
              )}
              {m.chart && revealChart && <ChartRenderer chart={m.chart} instant={instant} />}
              {m.done && revealChart && (
                <FollowUpChips suggestions={m.followups} onPick={onPickFollowup} disabled={streaming} />
              )}
              {m.done && revealChart && m.sql && (
                <button
                  onClick={() => onShowSql(m.id)}
                  className="mt-3 flex items-center gap-1.5 text-xs font-medium text-slate-500 transition hover:text-teal-600"
                >
                  <Code2 className="h-3.5 w-3.5" />
                  Show me the SQL
                </button>
              )}
            </>
          )}
        </div>
      </div>
    </motion.div>
  );
}
