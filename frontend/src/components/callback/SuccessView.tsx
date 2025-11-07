import { Badge } from "@/components/ui/badge";
import { CardDescription, CardTitle } from "@/components/ui/card";
import { CheckCircle } from "lucide-react";
import { cn } from "@/lib/utils";

export function SuccessView() {
  return (
    <>
      <div
        className={cn(
          "relative flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br shadow-lg",
          "shadow-emerald-500/20",
          "from-emerald-500/25 via-emerald-500/15 to-emerald-500/5"
        )}
      >
        <span className="absolute inset-0 rounded-2xl border border-emerald-500/40" />
        <CheckCircle className="h-8 w-8 text-emerald-500" />
      </div>

      <div className="space-y-3">
        <Badge
          variant="outline"
          className={cn(
            "border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
          )}
        >
          Spotify connected
        </Badge>
        <CardTitle className="text-3xl font-semibold">
          You&apos;re all set!
        </CardTitle>
        <CardDescription className="text-base text-muted-foreground">
          Spotify granted access and your Moodlist session is ready.
        </CardDescription>
      </div>
    </>
  );
}
