'use client';

import { useAuth } from '@/lib/store/authStore';
import type { User as UserType } from '@/lib/types/auth';
import { logger } from '@/lib/utils/logger';
import { AnimatePresence, motion } from '@/components/ui/lazy-motion';
import { ChevronDown, LogOut, User } from 'lucide-react';
import Link from 'next/link';
import { useState } from 'react';
import { UserAvatar } from '@/components/ui/UserAvatar';
import { DROPDOWN_VARIANTS } from '@/lib/constants/animations';
import { cn } from '@/lib/utils';

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
                onClick={() => setIsOpen((prev) => !prev)}
                className="hidden lg:flex items-center space-x-2 px-3 h-10 rounded-lg text-sm font-medium text-foreground hover:bg-accent/50 transition-all active:scale-95"
            >
                <UserAvatar user={user} size="md" withMotion />
                <span className="hidden sm:block max-w-24 truncate" title={user.display_name}>
                    {user.display_name}
                </span>
                <div
                    className={cn('transition-transform duration-200', isOpen ? 'rotate-180' : 'rotate-0')}
                >
                    <ChevronDown className="w-4 h-4 text-muted-foreground" />
                </div>
            </button>

            {/* Mobile - Non-clickable profile picture */}
            <div className="lg:hidden h-9 sm:h-10 flex items-center">
                <UserAvatar user={user} size="md" />
            </div>

            {/* Dropdown Menu */}
            <AnimatePresence>
                {isOpen && (
                    <>
                        <motion.div
                            variants={DROPDOWN_VARIANTS}
                            initial="closed"
                            animate="open"
                            exit="closed"
                            className="absolute right-0 top-full mt-2 w-56 bg-background/95 backdrop-blur-xl border rounded-xl shadow-2xl z-50 overflow-hidden"
                        >
                            {/* User Info Header */}
                            <div className="px-4 py-3 border-b bg-accent/50">
                                <p className="text-sm font-semibold text-foreground truncate">
                                    {user.display_name}
                                </p>
                                <p className="text-xs text-muted-foreground truncate">
                                    {user.email}
                                </p>
                            </div>

                            {/* Menu Items */}
                            <div className="p-2">
                                <Link
                                    href="/profile"
                                    onClick={() => setIsOpen(false)}
                                    className="w-full flex items-center space-x-3 px-3 py-2.5 text-sm font-medium text-foreground hover:bg-accent rounded-lg transition-all group"
                                >
                                    <User className="w-4 h-4 text-muted-foreground group-hover:text-primary transition-colors" />
                                    <span>View Profile</span>
                                </Link>

                                <div className="my-1 border-t" />

                                <button
                                    onClick={handleLogout}
                                    className="w-full flex items-center space-x-3 px-3 py-2.5 text-sm font-medium text-red-600 hover:bg-red-50 dark:hover:bg-red-950/20 rounded-lg transition-all group"
                                >
                                    <LogOut className="w-4 h-4" />
                                    <span>Sign Out</span>
                                </button>
                            </div>
                        </motion.div>

                        {/* Click outside to close */}
                        <div
                            className="fixed inset-0 z-40"
                            onClick={() => setIsOpen(false)}
                        />
                    </>
                )}
            </AnimatePresence>
        </div>
    );
}
