import { useEffect, useRef, useState } from "react";

interface Props {
  text: string; // accumulated target text (may keep growing as tokens arrive)
  done: boolean;
  onComplete?: () => void;
  instant?: boolean; // already revealed -> show full text immediately, no typing/cursor
}

const WORD_INTERVAL_MS = 38; // steady reveal cadence, independent of network chunks

// Reveals `text` word-by-word with requestAnimationFrame smoothing + a blinking
// cursor until complete. Smooths the backend's ~4-word chunks into a steady type.
export function StreamingText({ text, done, onComplete, instant = false }: Props) {
  const words = text.length ? text.split(" ") : [];
  const [revealed, setRevealed] = useState(instant ? words.length : 0);
  const startRef = useRef<number | null>(null);
  const rafRef = useRef<number>();
  const firedComplete = useRef(false);

  useEffect(() => {
    if (instant || revealed >= words.length) return;
    startRef.current = null;
    const step = (t: number) => {
      if (startRef.current === null) startRef.current = t;
      if (t - startRef.current >= WORD_INTERVAL_MS) {
        setRevealed((r) => Math.min(r + 1, words.length));
      } else {
        rafRef.current = requestAnimationFrame(step);
      }
    };
    rafRef.current = requestAnimationFrame(step);
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, [instant, revealed, words.length]);

  const shown = words.slice(0, revealed).join(" ");
  const complete = instant || (done && revealed >= words.length);

  useEffect(() => {
    if (complete && !firedComplete.current) {
      firedComplete.current = true;
      onComplete?.();
    }
  }, [complete, onComplete]);

  return (
    <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-700">
      {shown}
      {!complete && (
        <span className="ml-0.5 inline-block h-4 w-[2px] translate-y-0.5 animate-pulse bg-teal-500 align-middle" />
      )}
    </p>
  );
}
