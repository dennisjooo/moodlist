'use client';

import { ThemeToggle } from '@/components/ThemeToggle';
import { AnimatePresence, motion } from '@/components/ui/lazy-motion';
import { BUTTON_MOTION_PROPS, MENU_ITEM_VARIANTS, MOBILE_MENU_VARIANTS, SPRING_TRANSITIONS } from '@/lib/constants/animations';
import { useAuth } from '@/lib/contexts/AuthContext';
import type { User as UserType } from '@/lib/types/auth';
import { NavItem } from '@/lib/types/navigation';
import { logger } from '@/lib/utils/logger';
import { LogOut, Menu, User, X } from 'lucide-react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';

interface MobileMenuProps {
    items: NavItem[];
    user?: UserType | null;
    onProfileClick?: () => void;
}

export function MobileMenu({ items, user, onProfileClick }: MobileMenuProps) {
    const [isOpen, setIsOpen] = useState(false);
    const [mounted, setMounted] = useState(false);
    const { logout } = useAuth();
    const pathname = usePathname();

    useEffect(() => {
        setMounted(true);
    }, []);

    const handleLogout = async () => {
        try {
            await logout();
            setIsOpen(false);
        } catch (error) {
            logger.error('Logout failed', error, { component: 'MobileMenu' });
        }
    };

    return (
        <>
            {/* Mobile Menu Button */}
            <motion.button
                onClick={() => setIsOpen(!isOpen)}
                className="lg:hidden p-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-accent/50 transition-colors"
                aria-label="Toggle menu"
                {...BUTTON_MOTION_PROPS}
            >
                <AnimatePresence mode="wait" initial={false}>
                    <motion.div
                        key={isOpen ? 'close' : 'open'}
                        initial={{ rotate: -90, opacity: 0 }}
                        animate={{ rotate: 0, opacity: 1 }}
                        exit={{ rotate: 90, opacity: 0 }}
                        transition={{ duration: 0.2 }}
                    >
                        {isOpen ? (
                            <X className="w-5 h-5" />
                        ) : (
                            <Menu className="w-5 h-5" />
                        )}
                    </motion.div>
                </AnimatePresence>
            </motion.button>

            {/* Mobile Menu Dropdown - Rendered via Portal */}
            {mounted && createPortal(
                <AnimatePresence>
                    {isOpen && (
                        <>
                            {/* Backdrop */}
                            <motion.div
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                exit={{ opacity: 0 }}
                                transition={{ duration: 0.2 }}
                                className="fixed inset-0 bg-black/20 z-40 lg:hidden"
                                onClick={() => setIsOpen(false)}
                                aria-hidden="true"
                            />

                            <motion.div
                                variants={MOBILE_MENU_VARIANTS}
                                initial="closed"
                                animate="open"
                                exit="closed"
                                className="lg:hidden fixed right-4 top-[4.5rem] w-72 border rounded-xl shadow-2xl bg-background/95 backdrop-blur-xl overflow-hidden z-50"
                            >
                            <div className="p-2">
                                {/* Navigation Links */}
                                {items.map((item) => {
                                    const isActive = pathname === item.href;
                                    return (
                                        <motion.div key={item.name} variants={MENU_ITEM_VARIANTS}>
                                            <Link
                                                href={item.href}
                                                className={`relative flex items-center px-4 py-2.5 rounded-lg text-sm font-medium transition-colors group overflow-hidden ${isActive
                                                    ? 'text-foreground bg-accent/50'
                                                    : 'text-muted-foreground hover:text-foreground hover:bg-accent/50'
                                                    }`}
                                                onClick={() => setIsOpen(false)}
                                            >
                                                <span className="relative z-10">{item.name}</span>
                                                {isActive && (
                                                    <motion.div
                                                        className="absolute left-1 top-1/2 -translate-y-1/2 w-1 h-6 bg-primary rounded-full"
                                                        layoutId="activeMobileTab"
                                                        transition={SPRING_TRANSITIONS.snappy}
                                                    />
                                                )}
                                            </Link>
                                        </motion.div>
                                    );
                                })}

                                {/* Divider */}
                                {user && (
                                    <motion.div variants={MENU_ITEM_VARIANTS} className="my-2 border-t" />
                                )}

                                {/* User Actions */}
                                {user && (
                                    <>
                                        <motion.div variants={MENU_ITEM_VARIANTS}>
                                            <Link
                                                href="/profile"
                                                className="flex items-center space-x-3 px-4 py-2.5 rounded-lg text-sm font-medium text-foreground hover:bg-accent/50 transition-colors group"
                                                onClick={() => {
                                                    setIsOpen(false);
                                                    onProfileClick?.();
                                                }}
                                            >
                                                <User className="w-4 h-4 text-muted-foreground group-hover:text-primary transition-colors" />
                                                <span>View Profile</span>
                                            </Link>
                                        </motion.div>

                                        <motion.div variants={MENU_ITEM_VARIANTS}>
                                            <button
                                                onClick={handleLogout}
                                                className="w-full flex items-center space-x-3 px-4 py-2.5 rounded-lg text-sm font-medium text-red-600 hover:bg-red-50 dark:hover:bg-red-950/20 transition-colors group"
                                            >
                                                <LogOut className="w-4 h-4" />
                                                <span>Sign Out</span>
                                            </button>
                                        </motion.div>
                                    </>
                                )}

                                {/* Theme Toggle */}
                                <motion.div variants={MENU_ITEM_VARIANTS} className="mt-2 pt-2 border-t">
                                    <div className="px-4 py-2">
                                        <div className="flex items-center justify-between">
                                            <span className="text-sm font-medium text-muted-foreground">
                                                Theme
                                            </span>
                                            <ThemeToggle />
                                        </div>
                                    </div>
                                </motion.div>
                            </div>
                        </motion.div>
                    </>
                )}
            </AnimatePresence>,
            document.body
        )}
        </>
    );
}
