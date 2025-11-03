import { motion } from "framer-motion";
import { Card } from "@/components/ui/card";
import { type ReactNode } from "react";

interface CallbackCardProps {
  children: ReactNode;
  animate?: boolean;
}

export function CallbackCard({ children, animate = true }: CallbackCardProps) {
  const cardContent = (
    <Card className="relative w-full overflow-hidden border border-border/50 bg-background/80 backdrop-blur-xl shadow-2xl shadow-primary/5 dark:shadow-black/20">
      <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-primary/40 to-transparent" />
      {children}
    </Card>
  );

  if (!animate) {
    return <div className="w-full max-w-xl">{cardContent}</div>;
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: "easeOut" }}
      className="w-full max-w-xl"
    >
      {cardContent}
    </motion.div>
  );
}
