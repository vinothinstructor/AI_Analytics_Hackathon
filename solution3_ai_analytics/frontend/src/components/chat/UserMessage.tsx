import { motion } from "framer-motion";

export function UserMessage({ text }: { text: string }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex justify-end"
    >
      <div className="max-w-[85%] rounded-2xl rounded-br-sm bg-navy px-3.5 py-2 text-sm text-white">
        {text}
      </div>
    </motion.div>
  );
}
