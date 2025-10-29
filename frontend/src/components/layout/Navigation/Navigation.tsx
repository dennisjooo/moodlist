'use client';

import { SpotifyLoginButton } from '@/components/features/auth/SpotifyLoginButton';
import { ThemeToggle } from '@/components/ThemeToggle';
import { WorkflowNotificationIndicator } from '@/components/features/workflow/WorkflowNotificationIndicator';
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
        <nav className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 sticky top-0 z-50">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="flex justify-between items-center h-16 lg:justify-center lg:relative">
                    {/* Logo - Left Side */}
                    <div className="lg:absolute lg:left-0">
                        <Brand />
                    </div>

                    {/* Desktop Navigation Links - Center */}
                    <DesktopLinks items={navItems} />

                    {/* Right Side - Profile & Mobile Menu Button */}
                    <div className="flex items-center space-x-2 sm:space-x-4 lg:absolute lg:right-0">
                        {/* Workflow Notification Indicator */}
                        <WorkflowNotificationIndicator />

                        {/* Auth/Profile - Shows before burger on mobile */}
                        <div className="order-1 lg:order-none">
                            {isAuthenticated && user ? (
                                <AuthMenu user={user} />
                            ) : (
                                <SpotifyLoginButton className="bg-[#1DB954] hover:bg-[#1ed760] text-white h-8 px-3 text-sm rounded-md font-medium transition-all duration-200 flex items-center gap-1.5 shadow-md hover:shadow-lg sm:h-10 sm:px-6 sm:text-base sm:gap-2" />
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
