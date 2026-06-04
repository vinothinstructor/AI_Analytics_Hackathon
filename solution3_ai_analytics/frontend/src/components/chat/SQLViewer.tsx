import { useEffect, useState } from "react";

const INJECTED = "-- auto-injected";

// Fine-grained Shiki: only the SQL grammar + github-dark theme + the JS regex
// engine are bundled (no wasm, no other languages). Highlighter is created once.
let highlighterPromise: Promise<{ codeToHtml: (code: string, opts: any) => string }> | null = null;
function getHighlighter() {
  if (!highlighterPromise) {
    highlighterPromise = (async () => {
      const [{ createHighlighterCore }, { createJavaScriptRegexEngine }, sql, githubDark] =
        await Promise.all([
          import("shiki/core"),
          import("shiki/engine/javascript"),
          import("shiki/langs/sql.mjs"),
          import("shiki/themes/github-dark.mjs"),
        ]);
      return createHighlighterCore({
        themes: [githubDark.default],
        langs: [sql.default],
        engine: createJavaScriptRegexEngine(),
      });
    })();
  }
  return highlighterPromise;
}

// Pre-warm the highlighter at module load so the SQL is highlighted and ready by
// the time the Behind-the-scenes panel opens — no async "pop"/second reflow.
void getHighlighter().catch(() => {});

// Renders SQL on a dark navy block, syntax-highlighted via Shiki, with the
// auto-injected tenant line emphasized in teal (the credibility moment). Falls
// back to a plain highlighted block if Shiki fails to load.
export function SQLViewer({ sql }: { sql: string }) {
  const [html, setHtml] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const targets = sql
      .split("\n")
      .map((l, i) => (l.includes(INJECTED) ? i + 1 : 0))
      .filter(Boolean);

    getHighlighter()
      .then((hl) =>
        hl.codeToHtml(sql, {
          lang: "sql",
          theme: "github-dark",
          transformers: [
            {
              line(this: any, node: any, lineNumber: number) {
                if (targets.includes(lineNumber)) this.addClassToHast(node, "injected-line");
              },
            },
          ],
        }),
      )
      .then((out) => !cancelled && setHtml(out))
      .catch(() => !cancelled && setFailed(true));

    return () => {
      cancelled = true;
    };
  }, [sql]);

  if (html && !failed) {
    return (
      <div
        className="sql-shiki max-h-[60vh] overflow-auto rounded-lg text-[12.5px]"
        dangerouslySetInnerHTML={{ __html: html }}
      />
    );
  }

  // Fallback: plain dark block, teal highlight on the injected line.
  // Outer div scrolls; the <pre> carries the navy background and sizes to content
  // (min-w-max) so the background spans the full horizontal scroll width.
  return (
    <div className="max-h-[60vh] overflow-auto rounded-lg">
      <pre className="min-w-max bg-navy px-4 py-3.5 text-[12.5px] leading-[1.65] text-slate-200">
        <code className="font-mono">
        {sql.split("\n").map((line, i) => (
          <div
            key={i}
            className={
              line.includes(INJECTED)
                ? "-mx-4 border-l-2 border-teal-400 bg-teal-400/15 px-4 text-teal-200"
                : ""
            }
          >
            {line || " "}
          </div>
        ))}
        </code>
      </pre>
    </div>
  );
}
