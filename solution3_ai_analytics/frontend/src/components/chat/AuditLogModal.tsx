import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Loader2, X } from "lucide-react";

import { apiFetch } from "@/lib/apiFetch";
import { AuditRow } from "@/lib/types";
import { SQLViewer } from "./SQLViewer";

interface Props {
  queryId: string;
  onClose: () => void;
}

// Locale-independent UTC timestamp, deterministic on any machine for the recording.
function fmtUtc(iso: string): string {
  return new Date(iso).toISOString().slice(0, 16).replace("T", " ") + " UTC";
}

// Fetches GET /audit/{query_id} and shows the full audit trail. Dismissable via
// close button, overlay click, or Esc.
export function AuditLogModal({ queryId, onClose }: Props) {
  const [row, setRow] = useState<AuditRow | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  useEffect(() => {
    let cancelled = false;
    setRow(null);
    setError(null);
    apiFetch(`/audit/${queryId}`)
      .then(async (r) => {
        if (!r.ok) throw new Error(`Audit lookup failed (${r.status}).`);
        return r.json();
      })
      .then((data) => !cancelled && setRow(data))
      .catch((e) => !cancelled && setError(e.message || "Failed to load audit record."));
    return () => {
      cancelled = true;
    };
  }, [queryId]);

  const field = (label: string, value: React.ReactNode) => (
    <div className="flex justify-between gap-4 border-b border-slate-100 py-1.5 text-sm last:border-0">
      <span className="text-slate-400">{label}</span>
      <span className="text-right font-medium text-slate-700">{value}</span>
    </div>
  );

  return (
    <AnimatePresence>
      <motion.div
        className="fixed inset-0 z-[60] flex items-center justify-center bg-black/40 p-6"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onClose}
      >
        <motion.div
          className="max-h-[85vh] w-full max-w-lg overflow-auto rounded-2xl bg-white shadow-2xl"
          initial={{ scale: 0.96, y: 8 }}
          animate={{ scale: 1, y: 0 }}
          exit={{ scale: 0.96, y: 8 }}
          onClick={(e) => e.stopPropagation()}
        >
          <header className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
            <div className="text-sm font-semibold text-navy">Audit trail</div>
            <button onClick={onClose} className="rounded p-1 text-slate-400 hover:bg-slate-100" aria-label="Close">
              <X className="h-4 w-4" />
            </button>
          </header>

          <div className="p-4">
            {!row && !error && (
              <div className="flex items-center gap-2 py-6 text-sm text-slate-400">
                <Loader2 className="h-4 w-4 animate-spin" /> Loading audit record…
              </div>
            )}
            {error && <div className="py-6 text-sm text-red-600">{error}</div>}
            {row && (
              <>
                {field("Query ID", <span className="font-mono">{row.query_id}</span>)}
                {field("Sponsor / tenant", row.sponsor_id)}
                {field("Timestamp", fmtUtc(row.created_at))}
                {field("Latency", `${row.latency_ms} ms`)}
                {field("Rows returned", row.rows_returned)}
                {field("Tables used", row.tables_used.join(", ") || "—")}
                <div className="mt-3">
                  <div className="mb-1.5 text-xs font-medium uppercase tracking-wide text-slate-400">
                    Executed SQL
                  </div>
                  <SQLViewer sql={row.sql} />
                </div>
              </>
            )}
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
