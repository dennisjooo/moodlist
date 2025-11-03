import { type ReactNode } from "react";
import { DotPattern } from "@/components/ui/dot-pattern";

interface CallbackLayoutProps {
  children: ReactNode;
}

export function CallbackLayout({ children }: CallbackLayoutProps) {
  return (
    <div className="relative isolate min-h-screen overflow-hidden bg-gradient-to-br from-background via-background/95 to-muted">
      <div className="pointer-events-none absolute inset-0 opacity-80">
        <div className="absolute -left-24 top-0 h-72 w-72 rounded-full bg-primary/20 blur-3xl" />
        <div className="absolute right-12 top-40 h-64 w-64 rounded-full bg-primary/15 blur-3xl" />
        <div className="absolute bottom-[-5rem] left-1/2 h-80 w-80 -translate-x-1/2 rounded-full bg-emerald-500/10 blur-3xl" />
      </div>
      <DotPattern
        className="text-primary/10 [mask-image:radial-gradient(circle_at_center,white,transparent)]"
        width={28}
        height={28}
        glow
      />
      <div className="relative z-10 flex min-h-screen items-center justify-center p-6">
        {children}
      </div>
    </div>
  );
}
