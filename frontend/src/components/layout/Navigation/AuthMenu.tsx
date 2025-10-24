'use client';

import type { User as UserType } from '@/lib/types/auth';
import { logger } from '@/lib/utils/logger';
import { LogOut, User } from 'lucide-react';
import Image from 'next/image';
import Link from 'next/link';
import { useState } from 'react';
import { useAuth } from '@/lib/contexts/AuthContext';

interface AuthMenuProps {
    user: UserType;
}

export function AuthMenu({ user }: AuthMenuProps) {
    const [isOpen, setIsOpen] = useState(false);
    const { logout } = useAuth();

    const handleLogout = async () => {
        try {
            await logout();
            setIsOpen(false);
            // Navigation is handled by the logout function immediately
        } catch (error) {
            logger.error('Logout failed', error, { component: 'AuthMenu' });
        }
    };

    return (
        <div className="relative">
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="hidden lg:flex items-center space-x-2 text-sm font-medium text-foreground hover:text-primary transition-colors"
            >
                {user.profile_image_url ? (
                    <Image
                        src={user.profile_image_url}
                        alt={user.display_name}
                        width={32}
                        height={32}
                        className="w-8 h-8 rounded-full"
                    />
                ) : (
                    <div className="w-8 h-8 bg-primary/10 rounded-full flex items-center justify-center">
                        <User className="w-4 h-4 text-primary" />
                    </div>
                )}
                <span className="hidden sm:block max-w-24 truncate" title={user.display_name}>
                    {user.display_name}
                </span>
            </button>

            {/* Mobile - Non-clickable profile picture */}
            <div className="lg:hidden flex items-center">
                {user.profile_image_url ? (
                    <Image
                        src={user.profile_image_url}
                        alt={user.display_name}
                        width={32}
                        height={32}
                        className="w-8 h-8 rounded-full"
                    />
                ) : (
                    <div className="w-8 h-8 bg-primary/10 rounded-full flex items-center justify-center">
                        <User className="w-4 h-4 text-primary" />
                    </div>
                )}
            </div>

            {/* Dropdown Menu */}
            {isOpen && (
                <div className="absolute right-0 top-full mt-2 w-48 bg-background border rounded-lg shadow-lg z-50">
                    <div className="p-2">
                        <Link
                            href="/profile"
                            onClick={() => setIsOpen(false)}
                            className="w-full flex items-center space-x-2 px-3 py-2 text-sm text-foreground hover:bg-accent rounded-md transition-colors"
                        >
                            <User className="w-4 h-4" />
                            <span>View Profile</span>
                        </Link>
                        <hr className="my-1" />
                        <button
                            onClick={handleLogout}
                            className="w-full flex items-center justify-center space-x-2 px-3 py-2 text-sm text-red-600 hover:bg-red-50 rounded-md transition-colors"
                        >
                            <LogOut className="w-4 h-4" />
                            <span>Sign Out</span>
                        </button>
                    </div>
                </div>
            )}

            {/* Click outside to close */}
            {isOpen && (
                <div
                    className="fixed inset-0 z-40"
                    onClick={() => setIsOpen(false)}
                />
            )}
        </div>
    );
}
