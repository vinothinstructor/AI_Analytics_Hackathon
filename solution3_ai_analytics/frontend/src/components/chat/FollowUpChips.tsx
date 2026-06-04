import { motion } from "framer-motion";
import { ArrowUpRight } from "lucide-react";

interface Props {
  suggestions: string[];
  onPick: (q: string) => void;
  disabled?: boolean;
}

export function FollowUpChips({ suggestions, onPick, disabled }: Props) {
  if (!suggestions.length) return null;
  return (
    <div className="mt-3 flex flex-wrap gap-2">
      {suggestions.map((s, i) => (
        <motion.button
          key={s}
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15 + i * 0.08 }}
          disabled={disabled}
          onClick={() => onPick(s)}
          className="flex items-center gap-1 rounded-full border border-teal-500/40 bg-teal-50 px-3 py-1.5 text-xs font-medium text-teal-700 transition hover:bg-teal-100 disabled:opacity-50"
        >
          <ArrowUpRight className="h-3.5 w-3.5" />
          {s}
        </motion.button>
      ))}
    </div>
  );
}
