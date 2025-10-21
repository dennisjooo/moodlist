'use client';

import { ThemeToggle } from '@/components/ThemeToggle';
import type { User as UserType } from '@/lib/contexts/AuthContext';
import { initiateSpotifyAuth, isSpotifyAuthConfigured } from '@/lib/spotifyAuth';
import { Menu, User, X } from 'lucide-react';
import Link from 'next/link';
import { useState } from 'react';

interface NavItem {
    name: string;
    href: string;
}

interface MobileMenuProps {
    items: NavItem[];
    user?: UserType | null;
    onProfileClick?: () => void;
}

export function MobileMenu({ items, user, onProfileClick }: MobileMenuProps) {
    const [isOpen, setIsOpen] = useState(false);

    return (
        <>
            {/* Mobile Menu Button */}
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="lg:hidden p-2 rounded-md text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
                aria-label="Toggle menu"
            >
                {isOpen ? (
                    <X className="w-5 h-5" />
                ) : (
                    <Menu className="w-5 h-5" />
                )}
            </button>

            {/* Mobile Menu */}
            <div className={`lg:hidden border-t bg-background/95 backdrop-blur overflow-hidden transition-all duration-300 ease-in-out ${isOpen ? 'max-h-64 opacity-100' : 'max-h-0 opacity-0'}`}>
                <div className="px-2 pt-2 pb-3 space-y-1">
                    {items.map((item, index) => (
                        <Link
                            key={item.name}
                            href={item.href}
                            className={`block px-3 py-2 rounded-md text-sm font-medium text-muted-foreground hover:text-foreground hover:bg-accent transition-all duration-200 transform ${isOpen
                                ? 'translate-x-0 opacity-100'
                                : '-translate-x-4 opacity-0'
                                }`}
                            style={{
                                transitionDelay: isOpen ? `${index * 50}ms` : '0ms'
                            }}
                            onClick={() => setIsOpen(false)}
                        >
                            {item.name}
                        </Link>
                    ))}

                    {/* Profile Link in Mobile Menu */}
                    {user ? (
                        <Link
                            href="/profile"
                            className={`block px-3 py-2 rounded-md text-sm font-medium text-foreground hover:bg-accent transition-all duration-200 transform ${isOpen
                                ? 'translate-x-0 opacity-100'
                                : '-translate-x-4 opacity-0'
                                }`}
                            style={{
                                transitionDelay: isOpen ? `${(items.length - 1) * 50}ms` : '0ms'
                            }}
                            onClick={() => {
                                setIsOpen(false);
                                onProfileClick?.();
                            }}
                        >
                            <div className="flex items-center space-x-2">
                                <User className="w-4 h-4" />
                                <span>View Profile</span>
                            </div>
                        </Link>
                    ) : (
                        <button
                            onClick={() => {
                                if (!isSpotifyAuthConfigured()) {
                                    return;
                                }
                                initiateSpotifyAuth();
                                setIsOpen(false);
                            }}
                            className={`w-full text-left block px-3 py-2 rounded-md text-sm font-medium text-foreground hover:bg-accent transition-all duration-200 transform ${isOpen
                                ? 'translate-x-0 opacity-100'
                                : '-translate-x-4 opacity-0'
                                }`}
                            style={{
                                transitionDelay: isOpen ? `${(items.length - 1) * 50}ms` : '0ms'
                            }}
                        >
                            <div className="flex items-center space-x-2">
                                <svg
                                    className="w-4 h-4"
                                    viewBox="0 0 24 24"
                                    fill="currentColor"
                                    xmlns="http://www.w3.org/2000/svg"
                                >
                                    <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.42 1.56-.299.421-1.02.599-1.559.3z" />
                                </svg>
                                <span>Login</span>
                            </div>
                        </button>
                    )}

                    {/* Theme Toggle in Mobile Menu */}
                    <div className={`transform ${isOpen
                        ? 'translate-x-0 opacity-100'
                        : '-translate-x-4 opacity-0'
                        }`}
                        style={{
                            transitionDelay: isOpen ? `${items.length * 50}ms` : '0ms'
                        }}>
                        <div className="px-3 py-2">
                            <ThemeToggle />
                        </div>
                    </div>
                </div>
            </div>
        </>
    );
}
