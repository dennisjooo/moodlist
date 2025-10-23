'use client';

import { SpotifyLoginButton } from '@/components/features/auth/SpotifyLoginButton';
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
                    <div className="flex items-center space-x-4 lg:absolute lg:right-0">
                        {isAuthenticated && user ? (
                            <AuthMenu user={user} />
                        ) : (
                            <SpotifyLoginButton />
                        )}

                        {/* Theme Toggle - Hidden on mobile */}
                        <div className="hidden lg:block">
                            <ThemeToggle />
                        </div>

                        {/* Mobile Menu */}
                        <MobileMenu items={navItems} user={user} />
                    </div>
                </div>
            </div>
        </nav>
    );
}
