import { Badge } from '@/components/ui/badge';
import { Music } from 'lucide-react';
import Link from 'next/link';

interface BrandProps {
    href?: string;
}

export function Brand({ href = '/' }: BrandProps) {
    return (
        <Link href={href} className="flex items-center space-x-3">
            <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
                <Music className="w-4 h-4 text-primary-foreground" />
            </div>
            <span className="font-semibold text-xl">MoodList</span>
            <Badge variant="secondary" className="ml-2">Beta</Badge>
        </Link>
    );
}
