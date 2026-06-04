import { CheckCircle2, Circle } from "lucide-react";

import { TrustData } from "@/lib/types";

interface Props {
  trust: TrustData;
  onOpenAudit: (queryId: string) => void;
}

// Four data-driven trust badges. A passing check shows a green check; a false
// check shows a muted neutral state (truthful, not decorative).
export function TrustBadges({ trust, onOpenAudit }: Props) {
  const { checks, audit } = trust;
  const rows: { ok: boolean; node: React.ReactNode }[] = [
    { ok: checks.access_validated, node: "Validated against your access permissions" },
    { ok: checks.tenant_injected, node: "Tenant filter auto-injected — sponsor isolation enforced" },
    { ok: checks.read_only, node: "Read-only query · AST validator approved" },
    {
      ok: checks.audit_logged,
      node: (
        <span>
          Audit logged · Query ID:{" "}
          <button
            onClick={() => onOpenAudit(audit.query_id)}
            className="font-mono text-teal-600 underline decoration-dotted underline-offset-2 hover:text-teal-700"
          >
            {audit.query_id}
          </button>
        </span>
      ),
    },
  ];

  return (
    <div className="flex flex-col gap-2">
      {rows.map((r, i) => (
        <div key={i} className="flex items-start gap-2 text-sm">
          {r.ok ? (
            <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-status-ontrack" />
          ) : (
            <Circle className="mt-0.5 h-4 w-4 shrink-0 text-slate-300" />
          )}
          <span className={r.ok ? "text-slate-700" : "text-slate-400"}>{r.node}</span>
        </div>
      ))}
    </div>
  );
}
