// Recording-mode flags (read from the URL). Auto-type is opt-in insurance for
// the Round 2 video and ONLY available under ?recording=true.

function params(): URLSearchParams {
  if (typeof window === "undefined") return new URLSearchParams();
  return new URLSearchParams(window.location.search);
}

export function isRecording(): boolean {
  return params().get("recording") === "true";
}

// ?recording=true&autotype=1  -> auto-type the hero on panel open.
export function autoTypeEnabled(): boolean {
  if (!isRecording()) return false;
  const v = params().get("autotype");
  return v === "1" || v === "true";
}
