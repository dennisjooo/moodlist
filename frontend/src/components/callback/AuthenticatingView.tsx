import { Badge } from "@/components/ui/badge";
import { CardDescription, CardTitle } from "@/components/ui/card";
import { Music } from "lucide-react";
import { cn } from "@/lib/utils";

export function AuthenticatingView() {
  return (
    <>
      <div
        className={cn(
          "relative flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br shadow-lg",
          "shadow-primary/20",
          "from-primary/25 via-primary/10 to-primary/5"
        )}
      >
        <span className="absolute inset-0 rounded-2xl border border-primary/40 animate-pulse" />
        <Music className="h-8 w-8 text-primary" />
      </div>

      <div className="space-y-3">
        <Badge
          variant="outline"
          className={cn(
            "border-primary/20 bg-primary/10 text-primary"
          )}
        >
          Authenticating with Spotify
        </Badge>
        <CardTitle className="text-3xl font-semibold">
          Connecting your Spotify
        </CardTitle>
        <CardDescription className="text-base text-muted-foreground">
          Hang tight while we complete the secure login flow.
        </CardDescription>
      </div>
    </>
  );
}
