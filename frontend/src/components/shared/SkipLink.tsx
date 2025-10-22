'use client';

import { useSkipLink } from '@/lib/hooks/useAccessibility';
import { cn } from '@/lib/utils';

interface SkipLinkProps {
  targetId: string;
  children: React.ReactNode;
  className?: string;
}

/**
 * Skip link component for keyboard navigation
 * Allows keyboard users to skip to main content
 */
export function SkipLink({ targetId, children, className }: SkipLinkProps) {
  const { handleSkip } = useSkipLink(targetId);

  return (
    <a
      href={`#${targetId}`}
      onClick={handleSkip}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          handleSkip(e);
        }
      }}
      className={cn(
        'sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50',
        'focus:px-4 focus:py-2 focus:bg-primary focus:text-primary-foreground',
        'focus:rounded-md focus:outline-none focus:ring-2 focus:ring-ring',
        className
      )}
    >
      {children}
    </a>
  );
}

export default SkipLink;

