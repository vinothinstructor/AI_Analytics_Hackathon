import { useState } from "react";
import { X } from "lucide-react";

import { AIMessageT } from "@/lib/types";
import { AuditLogModal } from "./AuditLogModal";
import { SQLViewer } from "./SQLViewer";
import { TrustBadges } from "./TrustBadges";

interface Props {
  message: AIMessageT | null;
  onClose: () => void;
}

// The credibility surface: generated SQL (with the teal auto-injected line) +
// data-driven trust badges for the selected AI response. Neutral state when the
// selected response has no SQL (fast-path / decline / off-domain).
export function BehindTheScenesPanel({ message, onClose }: Props) {
  const [auditId, setAuditId] = useState<string | null>(null);
  const hasSql = !!message?.sql;

  return (
    <div className="flex h-full flex-col bg-slate-900 text-slate-200">
      <header className="flex items-center justify-between border-b border-white/10 px-4 py-3">
        <span className="text-xs font-semibold uppercase tracking-widest text-teal-400">
          Behind the scenes
        </span>
        <button onClick={onClose} className="rounded p-1 text-slate-400 hover:bg-white/10" aria-label="Close panel">
          <X className="h-4 w-4" />
        </button>
      </header>

      <div className="flex-1 overflow-y-auto p-4">
        {!hasSql ? (
          <div className="mt-10 text-center text-sm text-slate-400">
            No SQL for this response.
            <div className="mt-1 text-xs text-slate-500">
              (Presentation changes and declined questions don't run a query.)
            </div>
          </div>
        ) : (
          <>
            <section>
              <div className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-400">
                Generated SQL
              </div>
              <SQLViewer sql={message!.sql!.sql_display} />
            </section>

            {message!.trust && (
              <section className="mt-5 rounded-xl bg-white p-4">
                <div className="mb-2.5 text-xs font-medium uppercase tracking-wide text-slate-400">
                  Safety &amp; trust
                </div>
                <TrustBadges trust={message!.trust} onOpenAudit={setAuditId} />
              </section>
            )}
          </>
        )}
      </div>

      {auditId && <AuditLogModal queryId={auditId} onClose={() => setAuditId(null)} />}
    </div>
  );
}
