'use client';

import { SpotifyLoginButton } from '@/components/features/auth/SpotifyLoginButton';
import { WorkflowNotificationIndicator } from '@/components/features/workflow/WorkflowNotificationIndicator';
import { ThemeToggle } from '@/components/ThemeToggle';
import { useAuth } from '@/lib/contexts/AuthContext';
import { NavItem } from '@/lib/types/navigation';
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

export default function Navigation({ extraItems = [] }: NavigationProps) {
    const { user, isAuthenticated } = useAuth();

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
                        <Brand />
                    </div>

                    {/* Desktop Navigation Links - Center */}
                    <DesktopLinks items={navItems} />

                    {/* Right Side - Profile & Mobile Menu Button */}
                    <div className="flex items-center space-x-2 sm:space-x-3 lg:absolute lg:right-0">
                        {/* Workflow Notification Indicator */}
                        <WorkflowNotificationIndicator />

                        {/* Auth/Profile - Shows before burger on mobile */}
                        <div className="order-1 lg:order-none">
                            {isAuthenticated && user ? (
                                <AuthMenu user={user} />
                            ) : (
                                <SpotifyLoginButton className="bg-[#1DB954] hover:bg-[#1ed760] text-white h-9 px-4 text-sm rounded-lg font-semibold transition-all duration-200 flex items-center gap-2 shadow-md hover:shadow-lg hover:scale-105 sm:h-10 sm:px-6" />
                            )}
                        </div>

                        {/* Theme Toggle - Hidden on mobile */}
                        <div className="hidden lg:block">
                            <ThemeToggle />
                        </div>

                        {/* Mobile Menu Button - Shows last on mobile (right side) */}
                        <div className="lg:hidden order-2">
                            <MobileMenu items={navItems} user={user} />
                        </div>
                    </div>
                </div>
            </div>
        </nav>
    );
}
