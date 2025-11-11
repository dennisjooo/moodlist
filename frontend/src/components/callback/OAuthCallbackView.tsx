import { Button } from "@/components/ui/button";
import { CardContent, CardFooter, CardHeader } from "@/components/ui/card";
import { LoadingDots } from "@/components/ui/loading-dots";
import { useToast } from "@/lib/hooks/ui/useToast";
import type { AuthStatus } from "@/lib/hooks/useAuthCallback";
import { useEffect, useRef } from "react";
import { AuthenticatingView } from "./AuthenticatingView";
import { CallbackCard } from "./CallbackCard";
import { CallbackLayout } from "./CallbackLayout";
import { ErrorView } from "./ErrorView";
import { StatusProgress } from "./StatusProgress";
import { StepList } from "./StepList";
import { SuccessView } from "./SuccessView";

interface OAuthCallbackViewProps {
  status: AuthStatus;
  errorMessage: string;
  currentStage: number;
  redirectLabel: string;
  onRetry: () => void;
}

export function OAuthCallbackView({
  status,
  errorMessage,
  currentStage,
  redirectLabel,
  onRetry,
}: OAuthCallbackViewProps) {
  const { error: showErrorToast } = useToast();
  const errorToastShownRef = useRef<string | null>(null);

  useEffect(() => {
    if (status === "error" && errorMessage && errorToastShownRef.current !== errorMessage) {
      errorToastShownRef.current = errorMessage;
      showErrorToast("Authentication failed", {
        description: errorMessage,
        duration: 5000,
      });
    }
  }, [status, errorMessage, showErrorToast]);

  return (
    <CallbackLayout>
      <CallbackCard>
        <CardHeader className="flex flex-col items-center gap-5 text-center">
          {status === 'loading' && <AuthenticatingView />}
          {status === 'success' && <SuccessView />}
          {status === 'error' && <ErrorView />}
        </CardHeader>

        {status !== "error" && (
          <CardContent className="space-y-6 pb-8">
            <StatusProgress status={status} currentStage={currentStage} />
            <StepList status={status} currentStage={currentStage} />

            {status === "loading" && (
              <div className="flex flex-col items-center gap-2 text-sm text-muted-foreground">
                <LoadingDots size="md" />
                <span>This usually takes just a moment.</span>
              </div>
            )}

            {status === "success" && (
              <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 px-4 py-3 text-sm text-emerald-600 dark:text-emerald-300">
                Redirecting you to {redirectLabel}. Feel free to close this window if it
                doesn&apos;t move automatically.
              </div>
            )}
          </CardContent>
        )}

        {status === "error" && (
          <CardFooter className="pt-0">
            <Button onClick={onRetry} className="w-full">
              Return to home
            </Button>
          </CardFooter>
        )}
      </CallbackCard>
    </CallbackLayout>
  );
}
