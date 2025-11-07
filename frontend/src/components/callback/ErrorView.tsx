import { Badge } from "@/components/ui/badge";
import { CardDescription, CardTitle } from "@/components/ui/card";
import { XCircle } from "lucide-react";
import { cn } from "@/lib/utils";

export function ErrorView() {
  return (
    <>
      <div
        className={cn(
          "relative flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br shadow-lg",
          "shadow-destructive/20",
          "from-destructive/25 via-destructive/15 to-destructive/5"
        )}
      >
        <span className="absolute inset-0 rounded-2xl border border-destructive/40" />
        <XCircle className="h-8 w-8 text-destructive" />
      </div>

      <div className="space-y-3">
        <Badge
          variant="outline"
          className={cn(
            "border-destructive/40 bg-destructive/10 text-destructive"
          )}
        >
          Action needed
        </Badge>
        <CardTitle className="text-3xl font-semibold">
          We ran into an issue
        </CardTitle>
        <CardDescription className="text-base text-muted-foreground">
          Something interrupted the authentication. You can start the flow again from the home page.
        </CardDescription>
      </div>
    </>
  );
}
