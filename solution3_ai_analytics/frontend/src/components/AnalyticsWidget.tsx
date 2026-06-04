import { useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Layers, MessageSquare, Mic, Send, X } from "lucide-react";

import { useChat } from "@/hooks/useChat";
import { AIMessageT } from "@/lib/types";
import { cn } from "@/lib/utils";
import { apiFetch } from "@/lib/apiFetch";
import { autoTypeEnabled, isRecording } from "@/lib/recording";
import { ChatPanel } from "@/components/chat/ChatPanel";
import { BehindTheScenesPanel } from "@/components/chat/BehindTheScenesPanel";

const HERO_FALLBACK =
  "Which of my MOON-2026 sites are at risk of missing enrollment targets, and what's the 60-day trend?";
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

// Phase 3: live SSE chat. Phase 4: a collapsible "Behind the scenes" pane
// (generated SQL + data-driven trust badges + audit modal) for a selected response.
export function AnalyticsWidget() {
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState("");
  const [btsOpen, setBtsOpen] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const { messages, isStreaming, sendQuestion, markRevealed } = useChat();

  const submit = (q?: string) => {
    const text = (q ?? draft).trim();
    if (!text || isStreaming) return;
    sendQuestion(text);
    setDraft("");
  };

  // Recording-only auto-type insurance: types a question char-by-char into the
  // input (realistic cadence) then submits. The response is still the real
  // CACHED (captured-real-Azure) response. Opt-in only; never outside recording.
  const autoTyping = useRef(false);
  const autoTypeQuestion = async (question: string) => {
    if (autoTyping.current || isStreaming) return;
    autoTyping.current = true;
    setDraft("");
    for (let i = 1; i <= question.length; i++) {
      setDraft(question.slice(0, i));
      await sleep(50 + Math.random() * 30); // ~50–80ms/char
    }
    await sleep(300);
    autoTyping.current = false;
    submit(question);
  };
  const triggerAutoType = () => {
    apiFetch("/demo-questions")
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => autoTypeQuestion(d?.hero?.question || HERO_FALLBACK))
      .catch(() => autoTypeQuestion(HERO_FALLBACK));
  };

  // Auto-fire once on panel open when ?recording=true&autotype=1.
  const autoTypeFired = useRef(false);
  useEffect(() => {
    if (open && autoTypeEnabled() && !autoTypeFired.current && messages.length === 0) {
      autoTypeFired.current = true;
      triggerAutoType();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  // Manual trigger (recording only): F2 types the hero — a safety net on camera.
  useEffect(() => {
    if (!isRecording()) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "F2") {
        e.preventDefault();
        setOpen(true);
        triggerAutoType();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const latestSqlId = useMemo(() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      const m = messages[i];
      if (m.role === "ai" && m.sql) return m.id;
    }
    return null;
  }, [messages]);

  // Auto-follow: whenever a NEW SQL-bearing answer arrives (latestSqlId changes),
  // advance the panel's selection to it. An explicit "Show me the SQL" click
  // pins to that message until the next SQL answer arrives. Responses with no
  // SQL don't change latestSqlId, so the panel keeps showing the last real SQL.
  useEffect(() => {
    if (latestSqlId) setSelectedId(latestSqlId);
  }, [latestSqlId]);

  const selected = useMemo<AIMessageT | null>(() => {
    const m = messages.find((x) => x.id === selectedId);
    return m && m.role === "ai" ? m : null;
  }, [messages, selectedId]);

  const showSql = (id: string) => {
    setSelectedId(id);
    setBtsOpen(true);
  };
  const toggleBts = () => setBtsOpen((v) => !v);

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="fixed bottom-6 right-6 z-40 flex h-14 w-14 items-center justify-center rounded-full bg-teal-500 text-white shadow-lg transition hover:bg-teal-600"
        aria-label="Open AI Analytics"
      >
        <MessageSquare className="h-6 w-6" />
      </button>

      <AnimatePresence>
        {open && (
          <motion.aside
            key="widget"
            initial={{ x: "100%", width: "40vw" }}
            animate={{ x: 0, width: btsOpen ? "72vw" : "40vw" }}
            exit={{ x: "100%" }}
            transition={{ type: "tween", ease: "easeInOut", duration: 0.32 }}
            className="fixed right-0 top-0 z-50 flex h-full min-w-[420px] flex-col bg-white shadow-[-12px_0_32px_-8px_rgba(15,23,42,0.18)]"
          >
            {/* Header — fixed h-14 to match the OneHomeWrapper top bar exactly. */}
            <header className="flex h-14 items-center justify-between bg-navy px-4 text-white">
              <div>
                <div className="text-sm font-semibold">AI Analytics</div>
                <div className="text-xs text-slate-300">Helix Therapeutics · Ask about your studies</div>
              </div>
              <div className="flex items-center gap-1">
                <button
                  onClick={toggleBts}
                  className={cn(
                    "flex items-center gap-1.5 rounded-md px-2 py-1 text-xs transition",
                    btsOpen ? "bg-teal-500/20 text-teal-300" : "text-slate-300 hover:bg-navy-800",
                  )}
                  aria-label="Toggle behind the scenes"
                >
                  <Layers className="h-4 w-4" />
                  Behind the scenes
                </button>
                <button
                  onClick={() => setOpen(false)}
                  className="rounded p-1 text-slate-300 hover:bg-navy-800 hover:text-white"
                  aria-label="Close"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>
            </header>

            {/* Body: optional Behind-the-scenes pane + chat column.
                The chat column is a FIXED width (40vw) so it never reflows while
                the aside width animates open — the aside grows leftward and the
                Behind-the-scenes pane (flex-1) fills the newly-created space.
                BTS fades in with opacity only (no competing x-slide). */}
            <div className="flex min-h-0 flex-1">
              <AnimatePresence>
                {btsOpen && (
                  <motion.div
                    key="bts"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    transition={{ duration: 0.25, ease: "easeInOut" }}
                    className="min-w-0 flex-1 overflow-hidden border-r border-slate-200"
                  >
                    <BehindTheScenesPanel message={selected} onClose={() => setBtsOpen(false)} />
                  </motion.div>
                )}
              </AnimatePresence>

              <div className="flex w-[40vw] min-w-[420px] shrink-0 flex-col">
                <div className="flex-1 overflow-y-auto">
                  <ChatPanel
                    messages={messages}
                    streaming={isStreaming}
                    onSend={submit}
                    onShowSql={showSql}
                    onRevealed={markRevealed}
                  />
                </div>

                <div className="border-t border-slate-200 p-3">
                  <div className="flex items-center gap-2 rounded-xl border border-slate-300 px-3 py-2 focus-within:ring-2 focus-within:ring-teal-500">
                    <Mic className="h-5 w-5 text-slate-400" aria-label="Voice (not enabled)" />
                    <input
                      value={draft}
                      onChange={(e) => setDraft(e.target.value)}
                      onKeyDown={(e) => e.key === "Enter" && submit()}
                      placeholder="Ask about your studies, sites, enrollment…"
                      className="flex-1 bg-transparent text-sm outline-none"
                    />
                    <button
                      onClick={() => submit()}
                      disabled={isStreaming || !draft.trim()}
                      className="rounded-lg bg-teal-500 p-1.5 text-white transition hover:bg-teal-600 disabled:cursor-not-allowed disabled:opacity-40"
                      aria-label="Send"
                    >
                      <Send className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </motion.aside>
        )}
      </AnimatePresence>
    </>
  );
}
