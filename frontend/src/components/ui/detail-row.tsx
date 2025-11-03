import { cn } from '@/lib/utils';

interface DetailRowProps {
    icon: React.ComponentType<{ className?: string }>;
    children: React.ReactNode;
    className?: string;
}

export const DetailRow = ({ icon: Icon, children, className }: DetailRowProps) => (
    <div className={cn('flex items-center gap-2', className)}>
        <Icon className="w-3 h-3 text-muted-foreground/70 flex-shrink-0" />
        <span className="leading-snug">{children}</span>
    </div>
);

