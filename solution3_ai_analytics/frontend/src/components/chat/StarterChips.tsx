import { useEffect, useState } from "react";
import { Sparkles } from "lucide-react";

import { apiFetch } from "@/lib/apiFetch";

interface Props {
  onPick: (q: string) => void;
}

// Fallback if the curated source can't be fetched (keeps the demo robust).
const FALLBACK_STARTERS = [
  "Which of my MOON-2026 sites are at risk of missing enrollment targets, and what's the 60-day trend?",
  "What's the average screen-failure rate by country?",
  "Show login engagement trends over the last 90 days.",
];

export function StarterChips({ onPick }: Props) {
  // Read the curated starters from the single source of truth (demo_questions.yaml
  // via /demo-questions) so they stay in sync with the precache/library.
  const [starters, setStarters] = useState<string[]>(FALLBACK_STARTERS);

  useEffect(() => {
    apiFetch("/demo-questions")
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (d?.starters?.length) setStarters(d.starters);
      })
      .catch(() => {
        /* keep fallback */
      });
  }, []);

  return (
    <div className="flex h-full flex-col items-center justify-center px-6 text-center">
      <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-teal-50 text-teal-600">
        <Sparkles className="h-6 w-6" />
      </div>
      <p className="text-sm font-medium text-navy">Ask a question to get started</p>
      <p className="mt-1 text-xs text-slate-400">Try one of these:</p>
      <div className="mt-4 flex w-full flex-col gap-2">
        {starters.map((s) => (
          <button
            key={s}
            onClick={() => onPick(s)}
            className="rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-left text-xs text-slate-700 transition hover:border-teal-400 hover:bg-teal-50"
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  );
}
