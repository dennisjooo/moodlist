"use client";

import { Suspense } from "react";
import { Music } from "lucide-react";
import { CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { useAuth } from "@/lib/store/authStore";
import { useAuthCallback } from "@/lib/hooks/useAuthCallback";
import {
  CallbackLayout,
  CallbackCard,
  AlreadyAuthenticatedView,
  CheckingAuthView,
  OAuthCallbackView,
  StatusProgress,
  StepList,
} from "@/components/callback";

function CallbackContent() {
  const { isAuthenticated, isValidated, isLoading } = useAuth();
  const { status, errorMessage, errorType, currentStage, redirectLabel, handleRetry } = useAuthCallback();

  // Already authenticated - show success message and redirect
  if (isValidated && isAuthenticated) {
    return <AlreadyAuthenticatedView />;
  }

  // Checking auth status - prevent flash of OAuth UI
  if (!isValidated && isLoading) {
    return <CheckingAuthView />;
  }

  // OAuth callback flow
  return (
    <OAuthCallbackView
      status={status}
      errorMessage={errorMessage}
      errorType={errorType}
      currentStage={currentStage}
      redirectLabel={redirectLabel}
      onRetry={handleRetry}
    />
  );
}

function SuspenseFallback() {
  return (
    <CallbackLayout>
      <CallbackCard animate={false}>
        <CardHeader className="flex flex-col items-center gap-4 text-center">
          <div className="relative flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-primary/20 via-primary/10 to-primary/5 shadow-primary/20">
            <span className="absolute inset-0 rounded-2xl border border-primary/30 animate-pulse" />
            <Music className="h-8 w-8 text-primary" />
          </div>
          <CardTitle className="text-2xl font-semibold">Connecting to Spotify</CardTitle>
          <CardDescription className="text-base text-muted-foreground">
            Preparing your authentication session...
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6 pb-8">
          <StatusProgress status="loading" currentStage={0} />
          <StepList status="loading" currentStage={0} />
        </CardContent>
      </CallbackCard>
    </CallbackLayout>
  );
}

export default function CallbackPage() {
  return (
    <Suspense fallback={<SuspenseFallback />}>
      <CallbackContent />
    </Suspense>
  );
}
