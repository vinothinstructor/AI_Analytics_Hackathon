# 🎯 Judge Cheat Sheet — IQVIA AI Analytics (LIVE / Round 3)

**Steer the room:** *"Ask me about enrollment, sites, deviations, screening, or study activity."*

---

### Tier 1 — Rock-solid (lead with these)

1. Which of my MOON-2026 sites are at risk of missing enrollment targets, and what's the 60-day trend? → **bar**
2. *(chip)* Show the 60-day enrollment trend for the at-risk sites → **line**
3. What's driving the screen-failure rate at Tokyo? → **bar**
4. Where are my protocol deviations concentrated across MOON-2026 sites? → **bar**
5. How do site size and screen-failure rate relate for MOON-2026? → **scatter**
6. Show cumulative enrollment over the past year for MOON-2026. → **area**
7. Break down protocol deviations by severity. → **donut**
8. What's the visit completion mix for MOON-2026? → **pie**
9. Show screen-failure rates across my MOON-2026 sites. → **bar**

### Tier 2 — Safe extras (good "ask me anything" fallbacks)

- What's the average screen-failure rate by country?
- How many enrolled patients are in each study?
- Which sites have the most protocol deviations?
- List all sites in Germany.
- Which investigators specialize in Oncology?
- Count sites per country.
- Compare enrolled patients across all studies.
- How many patients consented versus were randomized?
- How many visits were completed versus missed?
- How many investigators are assigned per study?

### Tier 3 — "Knows its limits" (use to impress)

- What's the average age of the patients? → **graceful decline** (no age field — won't hallucinate)
- What's the weather today? → **off-domain decline** (stays in its lane)

### Tier 4 — The credibility flip (prepared move)

- Judge asks *"Are these real?"* → switch **CACHED → LIVE**, re-run **Q1** live. *(Rehearse this.)*

---

**Show the trust story:** "Show me the SQL" on Q1 → teal `-- auto-injected` tenant filter + audit modal.
**Quick win:** after any chart, say "show me as a pie chart" → instant re-render, no stage chips.

⚠️ Don't over-promise "ask anything" — gently steer toward the domain strengths above.
