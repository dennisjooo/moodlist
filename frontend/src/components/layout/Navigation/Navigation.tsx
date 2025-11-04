'use client';

import { SpotifyLoginButton } from '@/components/features/auth/SpotifyLoginButton';
import { WorkflowNotificationIndicator } from '@/components/features/workflow/WorkflowNotificationIndicator';
import { ThemeToggle } from '@/components/ThemeToggle';
import { useAuth } from '@/lib/contexts/AuthContext';
import { config } from '@/lib/config';
import { getCookie } from '@/lib/cookies';
import { NavItem } from '@/lib/types/navigation';
import { Skeleton } from '@/components/ui/skeleton';
import { useEffect, useState } from 'react';
import { LOGIN_BUTTON_CLASSES } from './constants';
import { AuthMenu } from './AuthMenu';
import { Brand } from './Brand';
import { DesktopLinks } from './DesktopLinks';
import { MobileMenu } from './MobileMenu';

interface NavigationProps {
    /** Optional override for branding link */
    logoHref?: string;
    /** Extra nav items beyond defaults */
    extraItems?: NavItem[];
}

// Skeleton loader for auth section to prevent layout shift
function AuthSkeleton() {
    return (
        <Skeleton shimmer={false} className="h-9 sm:h-10 w-32 sm:w-40 rounded-lg bg-accent/50" />
    );
}

export default function Navigation({ extraItems = [], logoHref }: NavigationProps) {
    const { user, isAuthenticated, isLoading } = useAuth();
    const [mounted, setMounted] = useState(false);
    const [hasAuthData, setHasAuthData] = useState<boolean | null>(null);

    useEffect(() => {
        setMounted(true);

        // Check if there's any auth data (session cookie or cache)
        // This helps us show login button immediately if user is definitely logged out
        const sessionCookie = getCookie(config.auth.sessionCookieName);
        const cachedAuth = typeof window !== 'undefined' ? sessionStorage.getItem(config.auth.cacheKey) : null;

        setHasAuthData(Boolean(sessionCookie || cachedAuth));
    }, []);

    const defaultNavItems: NavItem[] = [
        { name: 'Home', href: '/' },
        { name: 'Create', href: '/create' },
        { name: 'My Playlists', href: '/playlists' },
        { name: 'About', href: '/about' },
    ];

    const navItems = [...defaultNavItems, ...extraItems];

    return (
        <nav className="sticky top-0 z-50 border-b border-border/40 bg-background/80 backdrop-blur-xl supports-[backdrop-filter]:bg-background/60 shadow-sm">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="flex justify-between items-center h-16 lg:justify-center lg:relative">
                    {/* Logo - Left Side */}
                    <div className="lg:absolute lg:left-0">
                        <Brand href={logoHref} />
                    </div>

                    {/* Desktop Navigation Links - Center */}
                    <DesktopLinks items={navItems} />

                    {/* Right Side - Profile & Mobile Menu Button */}
                    <div className="flex items-center space-x-2 sm:space-x-3 lg:absolute lg:right-0">
                        {/* Workflow Notification Indicator */}
                        <WorkflowNotificationIndicator />

                        {/* Auth/Profile - Shows before burger on mobile */}
                        <div className="order-1 lg:order-none flex items-center">
                            {isAuthenticated && user ? (
                                <AuthMenu user={user} />
                            ) : hasAuthData === false ? (
                                // No auth data at all - show login button immediately
                                <SpotifyLoginButton className={LOGIN_BUTTON_CLASSES} />
                            ) : !mounted || isLoading || hasAuthData === null ? (
                                // Still loading or has auth data but user not loaded yet
                                <AuthSkeleton />
                            ) : (
                                <SpotifyLoginButton className={LOGIN_BUTTON_CLASSES} />
                            )}
                        </div>

                        {/* Theme Toggle - Hidden on mobile */}
                        <div className="hidden lg:block">
                            <ThemeToggle />
                        </div>

                        {/* Mobile Menu Button - Shows last on mobile (right side) */}
                        <div className="lg:hidden order-2 flex items-center">
                            <MobileMenu items={navItems} user={user} />
                        </div>
                    </div>
                </div>
            </div>
        </nav>
    );
}
