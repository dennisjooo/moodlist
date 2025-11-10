'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { NavItem } from '@/lib/types/navigation';
import { motion } from '@/components/ui/lazy-motion';
import { SPRING_TRANSITIONS } from '@/lib/constants/animations';
import { useRef } from 'react';

interface DesktopLinksProps {
    items: NavItem[];
}

export function DesktopLinks({ items }: DesktopLinksProps) {
    const pathname = usePathname();
    const containerRef = useRef<HTMLDivElement>(null);

    return (
        <div ref={containerRef} className="hidden lg:flex items-center space-x-1">
            {items.map((item) => {
                const isActive = pathname === item.href;
                return (
                    <Link
                        key={item.name}
                        href={item.href}
                        scroll={false}
                        className="relative px-4 py-2 group"
                    >
                        <span
                            className={`text-sm font-medium transition-colors relative z-10 ${isActive
                                ? 'text-foreground'
                                : 'text-muted-foreground hover:text-foreground'
                                }`}
                        >
                            {item.name}
                        </span>

                        {/* Hover background */}
                        <motion.div
                            className="absolute inset-0 bg-accent rounded-md opacity-0 group-hover:opacity-100"
                            initial={false}
                            transition={{ duration: 0.2 }}
                        />

                        {/* Active indicator underline */}
                        {isActive && (
                            <motion.div
                                className="absolute bottom-0 left-2 right-2 h-0.5 bg-primary rounded-full"
                                layoutId="activeTab"
                                layoutRoot={containerRef}
                                initial={false}
                                transition={SPRING_TRANSITIONS.snappy}
                            />
                        )}
                    </Link>
                );
            })}
        </div>
    );
}
