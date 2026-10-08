// Animates content open/closed (height + fade), including on exit, which CSS
// can't do for auto-height content. Used for the inline day viewers.

import { AnimatePresence, motion } from "motion/react";

const TRANSITION = { type: "spring", bounce: 0, visualDuration: 0.35 };

export default function Reveal({ show, children }) {
  return (
    <AnimatePresence initial={false}>
      {show && (
        <motion.div
          key="reveal"
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: "auto", opacity: 1 }}
          exit={{ height: 0, opacity: 0 }}
          transition={TRANSITION}
          style={{ overflow: "hidden" }}
        >
          {children}
        </motion.div>
      )}
    </AnimatePresence>
  );
}
