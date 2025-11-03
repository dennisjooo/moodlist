import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { CheckCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import { CallbackLayout } from "./CallbackLayout";
import { CallbackCard } from "./CallbackCard";

export function AlreadyAuthenticatedView() {
  const router = useRouter();

  useEffect(() => {
    const timer = setTimeout(() => {
      router.push('/');
    }, 2000);

    return () => clearTimeout(timer);
  }, [router]);

  return (
    <CallbackLayout>
      <CallbackCard>
        <CardHeader className="flex flex-col items-center gap-5 text-center">
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
              className="border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
            >
              Already authenticated
            </Badge>
            <CardTitle className="text-3xl font-semibold">
              You're good to go!
            </CardTitle>
            <CardDescription className="text-base text-muted-foreground">
              You're already logged in. Redirecting you to our homepage...
            </CardDescription>
          </div>
        </CardHeader>
      </CallbackCard>
    </CallbackLayout>
  );
}
