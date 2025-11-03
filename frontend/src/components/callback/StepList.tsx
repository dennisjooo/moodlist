import { Check, Loader2, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { AUTH_STEPS } from "@/lib/constants/auth";

interface StepListProps {
  status: 'loading' | 'success' | 'error';
  currentStage: number;
}

export function StepList({
  status,
  currentStage,
}: StepListProps) {
  return (
    <ul className="space-y-3">
      {AUTH_STEPS.map((step, index) => {
        const isActive = status === "loading" && index === currentStage;
        const isComplete =
          (status === "loading" && index < currentStage) ||
          (status === "success" && index <= currentStage) ||
          (status === "error" && index < currentStage);
        const isFailed = status === "error" && index === currentStage;

        return (
          <li
            key={step.title}
            className={cn(
              "flex items-start gap-4 rounded-xl border px-4 py-3 transition-colors",
              isFailed && "border-destructive/30 bg-destructive/5",
              !isFailed && isComplete && status === "success" && "border-emerald-500/30 bg-emerald-500/5",
              !isFailed && isComplete && status !== "success" && "border-primary/25 bg-primary/5",
              !isComplete && !isFailed && "border-border/40 bg-background/60"
            )}
          >
            <span
              className={cn(
                "mt-1 flex h-10 w-10 shrink-0 items-center justify-center rounded-full border text-sm font-semibold transition-colors",
                isFailed && "border-destructive/40 bg-destructive/10 text-destructive",
                !isFailed && isComplete && status === "success" && "border-emerald-500/40 bg-emerald-500/10 text-emerald-500",
                !isFailed && isComplete && status !== "success" && "border-primary/40 bg-primary/10 text-primary",
                isActive && "border-primary/40 bg-primary/10 text-primary animate-pulse",
                !isComplete && !isFailed && !isActive && "border-border/40 bg-background/80 text-muted-foreground"
              )}
            >
              {isFailed ? (
                <X className="h-4 w-4" />
              ) : isComplete ? (
                <Check className="h-4 w-4" />
              ) : isActive ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <span>{index + 1}</span>
              )}
            </span>
            <div className="space-y-1">
              <p
                className={cn(
                  "text-sm font-semibold",
                  isFailed && "text-destructive",
                  !isFailed && isComplete && status === "success" && "text-emerald-600 dark:text-emerald-400",
                  !isFailed && isComplete && status !== "success" && "text-primary"
                )}
              >
                {step.title}
              </p>
              <p className="text-sm text-muted-foreground">{step.description}</p>
            </div>
          </li>
        );
      })}
    </ul>
  );
}
