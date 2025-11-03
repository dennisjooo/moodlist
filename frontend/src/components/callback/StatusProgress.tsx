import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { AUTH_STEPS } from "@/lib/constants/auth";

interface StatusProgressProps {
    status: 'loading' | 'success' | 'error';
    currentStage: number;
}

export function StatusProgress({
    status,
    currentStage,
}: StatusProgressProps) {
    const totalSteps = AUTH_STEPS.length;
    const normalizedStage = Math.min(Math.max(currentStage, 0), totalSteps - 1);

    const statusLabel =
        status === 'success'
            ? 'Complete'
            : status === 'error'
                ? 'Needs attention'
                : `Step ${Math.min(normalizedStage + 1, totalSteps)} of ${totalSteps}`;

    return (
        <div
            className={cn(
                "rounded-2xl border px-5 py-4 transition-colors",
                status === "loading" && "border-primary/20 bg-primary/5",
                status === "success" && "border-emerald-500/30 bg-emerald-500/5",
                status === "error" && "border-destructive/30 bg-destructive/5"
            )}
        >
            <div className="flex items-center justify-between text-sm font-medium">
                <span className="text-muted-foreground">Status</span>
                <div className="flex items-center gap-2">
                    {status === "loading" && (
                        <Loader2 className="h-4 w-4 animate-spin text-primary" />
                    )}
                    <span
                        className={cn(
                            status === "loading" && "text-primary",
                            status === "success" && "text-emerald-600 dark:text-emerald-400",
                            status === "error" && "text-destructive"
                        )}
                    >
                        {statusLabel}
                    </span>
                </div>
            </div>
        </div>
    );
}
