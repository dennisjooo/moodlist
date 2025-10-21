'use client';

import { LoadingDots } from '@/components/ui/loading-dots';
import { ReactNode } from 'react';

interface PageLoadingStateProps {
  /**
   * Optional custom content to show instead of loading dots
   */
  children?: ReactNode;
  /**
   * Size of the loading dots
   */
  size?: 'sm' | 'md' | 'lg';
  /**
   * Custom className for the container
   */
  className?: string;
}

/**
 * Standard page loading state with centered content
 */
export default function PageLoadingState({ 
  children, 
  size = 'sm',
  className 
}: PageLoadingStateProps) {
  return (
    <div className={className || "flex items-center justify-center min-h-[60vh]"}>
      {children || (
        <div className="flex flex-col items-center gap-4">
          <LoadingDots size={size} />
        </div>
      )}
    </div>
  );
}

