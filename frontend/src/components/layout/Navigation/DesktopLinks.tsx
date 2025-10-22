import Link from 'next/link';
import { NavItem } from '@/lib/types/navigation';

interface DesktopLinksProps {
    items: NavItem[];
}

export function DesktopLinks({ items }: DesktopLinksProps) {
    return (
        <div className="hidden lg:flex items-center space-x-8">
            {items.map((item) => (
                <Link
                    key={item.name}
                    href={item.href}
                    className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
                >
                    {item.name}
                </Link>
            ))}
        </div>
    );
}
