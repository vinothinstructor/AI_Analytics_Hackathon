# Demo Questions — Solution 3 (IQVIA AI Analytics)

Two distinct lists, and the distinction matters for the live round:

- **List 1** — the 9 **scripted** questions you *built*. These have hand-authored,
  pixel-perfect responses; they're what you test now and use in the recorded video.
- **List 2** — the broader set to keep handy for the **live judge round (Round 3)**.
  Live you're in **LIVE** mode where the real LLM answers, so you can safely go beyond
  the scripted 9.

---

## LIST 1 — The 9 scripted questions (test these now)

Test the **hero arc (1–3)** as **one continuous conversation**. Test **4–9 each fresh**
(reopen the panel / new conversation — per the cache-key rule).

| # | Question | Expect | What to check |
|---|----------|--------|---------------|
| 1 | "Which of my MOON-2026 sites are at risk of missing enrollment targets, and what's the 60-day trend?" | Horizontal **bar** | Munich 82 green, São Paulo 67 amber, Tokyo 45 / Boston 38 / Toronto 28 red + status pills. Summary says "**stalled enrollment**" (not "declining"). 5 stages tick first. |
| 2 | *(chip)* "Show the 60-day enrollment trend for the at-risk sites" | Multi-**line** | Munich **blue** climbing; Tokyo (red) / Boston (orange) / Toronto (amber) flat near bottom. 4 distinct colors. |
| 3 | "What's driving the screen-failure rate at Tokyo?" | **bar** | Tokyo's ~29% screen-failure shown clearly. |
| 4 | "Where are my protocol deviations concentrated across MOON-2026 sites?" | **bar** (ranked) | Tokyo 40, Toronto 37, Boston 27 long bars; rest ≤6. Cluster obvious. |
| 5 | "How do site size and screen-failure rate relate for MOON-2026?" | **scatter** | Labeled axes; 3 red at-risk points top-left; green sites bottom-right. A relationship, not a blob. |
| 6 | "Show cumulative enrollment over the past year for MOON-2026." | **area** | Smooth teal curve 0→831; readable date axis. |
| 7 | "Break down protocol deviations by severity." | **donut** | Hole + minor 63% teal / major 26% amber / critical 12% red, with legend. |
| 8 | "What's the visit completion mix for MOON-2026?" | **pie** | Completed ~71% green / scheduled ~20% amber / missed ~10% red. |
| 9 | "Show screen-failure rates across my MOON-2026 sites." | **bar** (ranked) | 3 sites ~30%, then sharp drop to ~14% and below. |

### What to check on every one of the 9 — the same 4 questions

1. **Right chart type?** (matches the "Expect" column — not a table, not the wrong type)
2. **Right numbers?** (match the values above)
3. **Looks striking?** (a judge would lean in, not shrug)
4. **Reads in 2 seconds?** (the story is clear without studying it)

### Plus three behaviors to confirm once

- **"Show me the SQL"** on the hero → panel opens smoothly, teal `-- auto-injected` line
  visible, audit modal opens on the query ID.
- **Presentation fast-path:** after any chart, "show me as a pie chart" → instant
  re-render, no stage chips.
- **Graceful decline:** "What's the average age of the patients?" → polite decline, no
  data dump.

> Go through 1–9 and mark each **"good"** or **"problem: [what]."** Anything "problem"
> gets fixed before recording.

---

## LIST 2 — Questions to keep handy for the LIVE judge round (Round 3)

In Round 3 you're in **LIVE** mode, so the real LLM generates SQL on the spot — you're
*not* limited to the scripted 9. That's the whole point of "ask me anything." But you
still want a **safe, pre-tested** list to fall back on (and to offer judges if they
freeze). These are the ones the data probe + few-shot examples support well. Keep this on
a card.

### Tier 1 — your rock-solid scripted 9 (above)

If a judge says "show me something," lead with these — they're guaranteed.

### Tier 2 — pre-tested "safe extras"

Work respectably in FAKE, good LIVE candidates — these are in your `demo_questions.yaml`:

- "What's the average screen-failure rate by country?"
- "How many enrolled patients are in each study?"
- "Which sites have the most protocol deviations?"
- "List all sites in Germany."
- "Which investigators specialize in Oncology?"
- "Count sites per country."
- "Compare enrolled patients across all studies."
- "How many patients consented versus were randomized?"
- "How many visits were completed versus missed?"
- "How many investigators are assigned per study?"

### Tier 3 — the "knows its limits" demonstrators

Use these to *impress*, not avoid:

- "What's the average age of the patients?" → graceful decline (no age field) — shows the
  system won't hallucinate.
- "What's the weather today?" → off-domain decline — shows it stays in its lane.

### Tier 4 — the credibility flip (a prepared move, not a question)

- When a judge asks "are these real?" → switch **CACHED → LIVE** and re-run the hero
  question live. Have this rehearsed.

---

## Two important cautions for the live round

**Don't over-promise "ask anything."** LIVE generalization is strong but not infinite. If
a judge invites a question, gently steer toward the data's strengths — *"ask me about
enrollment, sites, deviations, screening, or study activity."* That frames the domain
without sounding limited, and keeps them in territory you've tested.

**One thing to actually test before Round 3** (on the office laptop, in LIVE): take 5–6
questions from **Tier 2 that are *not* in your cache** and run them in **real LIVE mode**
to confirm the live LLM handles them cleanly. This is the only way to know your "ask me
anything" actually holds — FAKE mode on the Mac uses heuristics, which is not the same as
the real LLM.

---

### Bottom line

- **Right now:** run **List 1** (the 9), report good/problem for each. That gates the
  recording.
- **List 2** is your live-round cheat sheet — keep it; pressure-test Tier 2 in real LIVE
  during the office-laptop session.
