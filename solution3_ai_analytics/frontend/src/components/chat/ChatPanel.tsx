import { useEffect, useRef } from "react";

import { ChatMessage } from "@/lib/types";
import { AIResponse } from "./AIResponse";
import { StarterChips } from "./StarterChips";
import { UserMessage } from "./UserMessage";

interface Props {
  messages: ChatMessage[];
  streaming: boolean;
  onSend: (q: string) => void;
  onShowSql: (id: string) => void;
  onRevealed: (id: string) => void;
}

export function ChatPanel({ messages, streaming, onSend, onShowSql, onRevealed }: Props) {
  const endRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to the newest content as it streams in.
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages]);

  if (messages.length === 0) {
    return <StarterChips onPick={onSend} />;
  }

  return (
    <div className="flex flex-col gap-4 p-4">
      {messages.map((m) =>
        m.role === "user" ? (
          <UserMessage key={m.id} text={m.text} />
        ) : (
          <AIResponse
            key={m.id}
            message={m}
            onPickFollowup={onSend}
            onShowSql={onShowSql}
            onRevealed={onRevealed}
            streaming={streaming}
          />
        ),
      )}
      <div ref={endRef} />
    </div>
  );
}
