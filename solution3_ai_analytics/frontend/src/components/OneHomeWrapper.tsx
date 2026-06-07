import { useEffect, useState, type ReactNode } from "react";
import { LayoutGrid, FileText, Users, Activity, FlaskConical } from "lucide-react";
import { apiFetch } from "@/lib/apiFetch";
import { ModeDropdown } from "@/components/ModeDropdown";
import { LLM_MODES, urlModeOverride, useModeStore, type LlmMode } from "@/store/modeStore";

// Mock "One Home for Sites" product shell. All data is synthetic and generated
// locally — this is purely a visual wrapper, not a real data source. Phase 4
// polishes it; Phase 1 just matches the layout/palette.
interface Study { code: string; name: string; phase: string; therapeutic_area: string }
interface OverviewStats {
  active_studies: number; total_sites: number; enrolled_patients: number;
  at_risk_sites: number; studies: Study[];
}

export function OneHomeWrapper({ children }: { children?: ReactNode }) {
  const [connected, setConnected] = useState<boolean | null>(null);
  const [latencyMs, setLatencyMs] = useState<number | null>(null);
  const [stats, setStats] = useState<OverviewStats | null>(null);
  const setMode = useModeStore((s) => s.setMode);

  // Health ping THROUGH apiFetch -> carries X-LLM-Mode and uses the /api proxy.
  useEffect(() => {
    const t0 = performance.now();
    apiFetch("/health")
      .then(async (r) => {
        setConnected(r.ok);
        setLatencyMs(Math.round(performance.now() - t0));
        // Seed the mode dropdown from the server's configured LLM_MODE (.env),
        // unless the URL explicitly sets ?mode=… (which wins).
        if (r.ok && !urlModeOverride()) {
          const m = (await r.json())?.llm_mode?.toUpperCase() as LlmMode | undefined;
          if (m && LLM_MODES.includes(m)) setMode(m);
        }
      })
      .catch(() => setConnected(false));
    // Real, tenant-scoped overview stats for the cards + recent-studies list.
    apiFetch("/overview-stats")
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => setStats(d))
      .catch(() => setStats(null));
  }, []);

  return (
    <div className="flex min-h-screen flex-col">
      {/* Top header — navy chrome. Fixed h-14 so the chat panel header (also h-14)
          lines up as one continuous top bar. */}
      <header className="flex h-14 items-center justify-between bg-navy px-6 text-white">
        <div className="flex items-center gap-3 text-sm">
          <span className="font-semibold tracking-wide">IQVIA · AI Analytics</span>
          <span className="text-slate-500">|</span>
          <span className="text-slate-300">One Home for Sites</span>
          <span className="text-slate-500">·</span>
          <span className="text-slate-300">Sponsor: Helix Therapeutics</span>
          <span className="text-slate-500">·</span>
          <span className="rounded bg-navy-800 px-2 py-0.5 text-xs text-slate-300">
            Read-only access
          </span>
        </div>
        <ModeDropdown />
      </header>

      {/* Connection status sub-bar */}
      <div className="flex items-center justify-between border-b border-slate-200 bg-white px-6 py-1.5 text-xs">
        <div className="flex items-center gap-2 text-slate-600">
          <span
            className={`inline-block h-2.5 w-2.5 rounded-full ${
              connected === false ? "bg-status-atrisk" : "bg-status-ontrack"
            }`}
          />
          <span>Connected to Sponsor Production · Multi-tenant access enforced · 8 clinical tables</span>
        </div>
        <span className="rounded-full bg-slate-100 px-2 py-0.5 font-medium text-slate-600">
          {latencyMs === null ? "…" : `${latencyMs} ms`}
        </span>
      </div>

      {/* Body: left nav + faux content */}
      <div className="flex flex-1">
        <nav className="w-52 shrink-0 border-r border-slate-200 bg-white p-3 text-sm text-slate-600">
          {[
            { icon: LayoutGrid, label: "Overview" },
            { icon: FlaskConical, label: "Studies" },
            { icon: Activity, label: "Sites" },
            { icon: Users, label: "Investigators" },
            { icon: FileText, label: "Reports" },
          ].map(({ icon: Icon, label }, i) => (
            <div
              key={label}
              className={`flex items-center gap-2 rounded-md px-3 py-2 ${
                i === 0 ? "bg-teal-500/10 font-medium text-teal-600" : "hover:bg-slate-100"
              }`}
            >
              <Icon className="h-4 w-4" />
              {label}
            </div>
          ))}
        </nav>

        <main className="flex-1 p-6">
          <h1 className="text-lg font-semibold text-navy">Sites Overview</h1>
          <p className="mt-1 text-sm text-slate-500">
            Synthetic demo data for Helix Therapeutics. Use the AI Analytics widget
            (bottom-right) to ask questions in plain English.
          </p>
          <div className="mt-6 grid grid-cols-3 gap-4">
            {[
              { label: "Active studies", value: stats?.active_studies },
              { label: "Sites", value: stats?.total_sites },
              { label: "Enrolled patients", value: stats?.enrolled_patients },
            ].map(({ label, value }) => (
              <div key={label} className="rounded-xl border border-slate-200 bg-white p-4">
                <div className="text-xs uppercase tracking-wide text-slate-400">{label}</div>
                {value === undefined ? (
                  <div className="mt-2 h-8 w-16 animate-pulse rounded bg-slate-100" />
                ) : (
                  <div className="mt-1 text-2xl font-semibold text-navy">
                    {value.toLocaleString()}
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Recent studies — a real, subdued product surface (chat widget stays the star). */}
          <div className="mt-6 rounded-xl border border-slate-200 bg-white">
            <div className="flex items-center justify-between border-b border-slate-100 px-4 py-2.5">
              <span className="text-sm font-medium text-navy">Recent studies</span>
              {stats && (
                <span className="text-xs text-slate-400">
                  {stats.at_risk_sites} sites at risk
                </span>
              )}
            </div>
            <div className="divide-y divide-slate-100">
              {(stats?.studies ?? []).map((s) => (
                <div key={s.code} className="flex items-center justify-between px-4 py-2.5 text-sm">
                  <div className="flex items-center gap-2">
                    <FlaskConical className="h-4 w-4 text-teal-600" />
                    <span className="font-medium text-navy">{s.code}</span>
                    <span className="text-slate-400">{s.name}</span>
                  </div>
                  <div className="flex items-center gap-2 text-xs text-slate-400">
                    <span>{s.therapeutic_area}</span>
                    <span className="rounded bg-slate-100 px-1.5 py-0.5">{s.phase}</span>
                  </div>
                </div>
              ))}
              {!stats && (
                <div className="px-4 py-6 text-center text-sm text-slate-400">Loading studies…</div>
              )}
            </div>
          </div>
        </main>
      </div>

      {children}
    </div>
  );
}
