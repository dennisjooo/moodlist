'use client';

import React, { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { LoadingDots } from '@/components/ui/loading-dots';
import { useAuth } from '@/lib/contexts/AuthContext';

interface AuthGuardProps {
  children: React.ReactNode;
  // If true, renders immediately with optimistic state
  allowOptimistic?: boolean;
  // Custom loading component
  fallback?: React.ReactNode;
  // Redirect destination if not authenticated
  redirectTo?: string;
}

export function AuthGuard({
  children,
  allowOptimistic = false,
  fallback,
  redirectTo = '/',
}: AuthGuardProps) {
  const { status } = useAuth();
  const router = useRouter();

  useEffect(() => {
    // Listen for auth expiration to redirect
    const handleExpired = () => {
      const redirect = window.location.pathname;
      router.push(`${redirectTo}?auth=expired&redirect=${redirect}`);
    };

    window.addEventListener('auth-expired', handleExpired);
    return () => window.removeEventListener('auth-expired', handleExpired);
  }, [router, redirectTo]);

  // Still checking for cookies
  if (status === 'initializing') {
    return (
      fallback || (
        <div className="flex items-center justify-center min-h-screen">
          <LoadingDots size="sm" />
        </div>
      )
    );
  }

  // Not authenticated
  if (status === 'unauthenticated') {
    router.push(`${redirectTo}?auth=required`);
    return null;
  }

  // Optimistic state - render immediately or wait for validation
  if (status === 'optimistic' && !allowOptimistic) {
    return (
      fallback || (
        <div className="flex items-center justify-center min-h-screen">
          <LoadingDots size="sm" />
        </div>
      )
    );
  }

  // Authenticated or optimistic (when allowed)
  return <>{children}</>;
}
