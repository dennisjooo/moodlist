import { Badge } from '@/components/ui/badge';
import { LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';

interface FeatureBadgeProps {
  icon?: LucideIcon;
  children: React.ReactNode;
  className?: string;
  iconClassName?: string;
  variant?: 'outline' | 'default' | 'secondary' | 'destructive';
  ariaLabel?: string;
}

/**
 * Reusable feature badge component with icon
 * Styled with rounded-full, backdrop-blur, and consistent spacing
 */
export function FeatureBadge({
  icon: Icon,
  children,
  className,
  iconClassName,
  variant = 'outline',
  ariaLabel,
}: FeatureBadgeProps) {
  return (
    <Badge
      variant={variant}
      className={cn(
        'mx-auto flex w-fit items-center gap-2 rounded-full border-border/60 bg-background/80 px-4 py-1 text-xs uppercase tracking-[0.24em] text-muted-foreground/80 backdrop-blur',
        className
      )}
      aria-label={ariaLabel}
    >
      {Icon && (
        <Icon
          className={cn('h-3.5 w-3.5 text-primary', iconClassName)}
          aria-hidden="true"
        />
      )}
      {children}
    </Badge>
  );
}

