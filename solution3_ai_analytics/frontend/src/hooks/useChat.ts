import { useCallback, useRef, useState } from "react";

import { apiFetch } from "@/lib/apiFetch";
import {
  AIMessageT, ChatMessage, StageName, StageStatus, emptyStages,
} from "@/lib/types";

let _seq = 0;
const newId = () => `m${Date.now()}_${_seq++}`;

function newConversationId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return `conv_${crypto.randomUUID()}`;
  }
  return `conv_${Date.now()}_${Math.floor(Math.random() * 1e6)}`;
}

/** Parse the SSE stream from a POST /chat response, invoking onEvent per frame. */
async function readSse(
  res: Response,
  onEvent: (type: string, data: any) => void,
): Promise<void> {
  const reader = res.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    // Frames are separated by a blank line.
    let sep: number;
    while ((sep = buffer.indexOf("\n\n")) !== -1) {
      const frame = buffer.slice(0, sep);
      buffer = buffer.slice(sep + 2);
      let evType = "message";
      const dataLines: string[] = [];
      for (const line of frame.split("\n")) {
        if (line.startsWith("event:")) evType = line.slice(6).trim();
        else if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
      }
      if (!dataLines.length) continue;
      let data: any = {};
      try {
        data = JSON.parse(dataLines.join("\n"));
      } catch {
        /* ignore malformed */
      }
      onEvent(evType, data);
    }
  }
}

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const conversationId = useRef<string>(newConversationId());

  // Mutate the in-flight AI message by id.
  const patchAi = useCallback((id: string, fn: (m: AIMessageT) => AIMessageT) => {
    setMessages((prev) =>
      prev.map((m) => (m.id === id && m.role === "ai" ? fn(m) : m)),
    );
  }, []);

  // Called once a message's first-arrival reveal animation finishes, so later
  // re-mounts render it statically.
  const markRevealed = useCallback(
    (id: string) => patchAi(id, (m) => (m.revealed ? m : { ...m, revealed: true })),
    [patchAi],
  );

  const sendQuestion = useCallback(
    async (question: string) => {
      const q = question.trim();
      if (!q || isStreaming) return;

      const userId = newId();
      const aiId = newId();
      const aiInit: AIMessageT = {
        id: aiId, role: "ai", stages: emptyStages(), hasStages: false,
        summary: "", followups: [], done: false, revealed: false,
      };
      setMessages((prev) => [
        ...prev,
        { id: userId, role: "user", text: q },
        aiInit,
      ]);
      setIsStreaming(true);

      try {
        const res = await apiFetch("/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ conversation_id: conversationId.current, question: q }),
        });

        // Fail-loud (e.g. LIVE without creds) returns JSON, not an event stream.
        const ctype = res.headers.get("content-type") || "";
        if (!res.ok || !ctype.includes("text/event-stream")) {
          let detail = `Request failed (${res.status}).`;
          try {
            const body = await res.json();
            detail = body.detail || body.message || detail;
          } catch {
            /* keep default */
          }
          patchAi(aiId, (m) => ({ ...m, error: detail, done: true }));
          return;
        }

        await readSse(res, (type, data) => {
          switch (type) {
            case "stage":
              patchAi(aiId, (m) => {
                const s = data.stage as StageName;
                const prev = m.stages[s];
                return {
                  ...m,
                  hasStages: true,
                  stages: {
                    ...m.stages,
                    [s]: {
                      status: data.status as StageStatus,
                      detail: data.detail ?? prev?.detail, // retain detail across running→done
                    },
                  },
                };
              });
              break;
            case "sql": // stored, not rendered (Phase 4)
              patchAi(aiId, (m) => ({ ...m, sql: data }));
              break;
            case "token":
              patchAi(aiId, (m) => ({ ...m, summary: m.summary + (data.text ?? "") }));
              break;
            case "chart":
              patchAi(aiId, (m) => ({ ...m, chart: { chart_spec: data.chart_spec, rows: data.rows } }));
              break;
            case "followups":
              patchAi(aiId, (m) => ({ ...m, followups: data.suggestions ?? [] }));
              break;
            case "trust": // stored, not rendered (Phase 4)
              patchAi(aiId, (m) => ({ ...m, trust: data }));
              break;
            case "error":
              patchAi(aiId, (m) => ({ ...m, error: data.message ?? "Something went wrong.", done: true }));
              break;
            case "done":
              patchAi(aiId, (m) => ({ ...m, done: true }));
              break;
          }
        });

        // Stream ended without an explicit done — finalize gracefully.
        patchAi(aiId, (m) => (m.done ? m : { ...m, done: true }));
      } catch (err) {
        patchAi(aiId, (m) => ({
          ...m,
          error: "I couldn't reach the server. Please check it's running and try again.",
          done: true,
        }));
      } finally {
        setIsStreaming(false);
      }
    },
    [isStreaming, patchAi],
  );

  return { messages, isStreaming, sendQuestion, markRevealed, conversationId: conversationId.current };
}
