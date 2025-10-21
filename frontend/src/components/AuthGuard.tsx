'use client';

import { ReactNode, useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useAuth } from '@/lib/contexts/AuthContext';
import { logger } from '@/lib/utils/logger';

interface AuthGuardProps {
    children: ReactNode;
    /**
     * If true, renders children immediately with optimistic auth state.
     * If false, waits for validation before rendering.
     * Default: true
     */
    optimistic?: boolean;
    /**
     * Custom loading component to show while validating auth
     */
    loadingComponent?: ReactNode;
    /**
     * Redirect path for unauthenticated users
     * Default: '/'
     */
    redirectTo?: string;
}

/**
 * AuthGuard component for protecting routes that require authentication.
 * 
 * Features:
 * - Optimistic rendering: Shows content immediately with cached auth state
 * - Background validation: Verifies auth in the background
 * - Automatic redirect: Redirects to login if not authenticated
 * - Flexible loading states: Configurable loading UI
 * 
 * @example
 * ```tsx
 * // Optimistic rendering (default)
 * <AuthGuard>
 *   <ProtectedContent />
 * </AuthGuard>
 * 
 * // Wait for validation
 * <AuthGuard optimistic={false}>
 *   <SensitiveContent />
 * </AuthGuard>
 * 
 * // Custom loading
 * <AuthGuard loadingComponent={<CustomSkeleton />}>
 *   <ProtectedContent />
 * </AuthGuard>
 * ```
 */
export function AuthGuard({
    children,
    optimistic = true,
    loadingComponent,
    redirectTo = '/',
}: AuthGuardProps) {
    const { isAuthenticated, isValidated, isLoading } = useAuth();
    const router = useRouter();
    const searchParams = useSearchParams();
    const [shouldRender, setShouldRender] = useState(optimistic);

    useEffect(() => {
        // If we're using optimistic rendering, show content immediately
        if (optimistic && isAuthenticated) {
            setShouldRender(true);
            return;
        }

        // If validation is complete
        if (isValidated) {
            if (!isAuthenticated) {
                // Not authenticated - redirect to login
                logger.info('AuthGuard: User not authenticated, redirecting', {
                    component: 'AuthGuard',
                    from: window.location.pathname,
                });

                const currentPath = window.location.pathname;
                const redirectUrl = `${redirectTo}?auth=required&redirect=${encodeURIComponent(currentPath)}`;
                router.push(redirectUrl);
                setShouldRender(false);
            } else {
                // Authenticated - show content
                setShouldRender(true);

                // If there's a redirect param, navigate to it (after successful auth)
                const redirectParam = searchParams.get('redirect');
                if (redirectParam) {
                    logger.info('AuthGuard: Redirecting to saved location', {
                        component: 'AuthGuard',
                        redirect: redirectParam,
                    });
                    router.push(redirectParam);
                }
            }
        }
    }, [isAuthenticated, isValidated, optimistic, router, searchParams, redirectTo]);

    // Show loading while initial validation is happening (non-optimistic mode)
    if (!optimistic && !isValidated && isLoading) {
        if (loadingComponent) {
            return <>{loadingComponent}</>;
        }

        // Default loading skeleton
        return (
            <div className="flex items-center justify-center min-h-screen">
                <div className="flex flex-col items-center gap-4">
                    <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin" />
                    <p className="text-muted-foreground">Verifying authentication...</p>
                </div>
            </div>
        );
    }

    // Don't render protected content if not authenticated
    if (!shouldRender) {
        return null;
    }

    return <>{children}</>;
}

/**
 * Higher-order component version of AuthGuard for wrapping page components
 * 
 * @example
 * ```tsx
 * const ProtectedPage = withAuthGuard(() => {
 *   return <div>Protected content</div>;
 * });
 * ```
 */
export function withAuthGuard<P extends object>(
    Component: React.ComponentType<P>,
    options?: Omit<AuthGuardProps, 'children'>
) {
    return function GuardedComponent(props: P) {
        return (
            <AuthGuard {...options}>
                <Component {...props} />
            </AuthGuard>
        );
    };
}

