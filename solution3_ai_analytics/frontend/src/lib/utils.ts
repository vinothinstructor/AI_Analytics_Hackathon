import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

// shadcn/ui className helper — present from Phase 1 so shadcn components
// (dialog, button, etc.) drop in cleanly when the audit modal lands in Phase 4.
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
