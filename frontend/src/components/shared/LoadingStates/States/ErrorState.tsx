'use client';

import { Button } from '@/components/ui/button';
import { AlertCircle } from 'lucide-react';

interface ErrorStateProps {
  /**
   * Error title
   */
  title?: string;
  /**
   * Error message to display
   */
  message: string;
  /**
   * Optional action button text
   */
  actionLabel?: string;
  /**
   * Optional action button handler
   */
  onAction?: () => void;
  /**
   * Custom className for the container
   */
  className?: string;
}

/**
 * Standard error state display
 */
export default function ErrorState({ 
  title = "Error",
  message,
  actionLabel,
  onAction,
  className 
}: ErrorStateProps) {
  return (
    <div className={className || "flex items-center justify-center min-h-[60vh]"}>
      <div className="text-center max-w-md">
        <div className="flex justify-center mb-4">
          <div className="w-12 h-12 rounded-full bg-destructive/10 flex items-center justify-center">
            <AlertCircle className="w-6 h-6 text-destructive" />
          </div>
        </div>
        <p className="text-lg font-semibold mb-2 text-destructive">{title}</p>
        <p className="text-muted-foreground mb-6">{message}</p>
        {actionLabel && onAction && (
          <Button onClick={onAction} variant="default">
            {actionLabel}
          </Button>
        )}
      </div>
    </div>
  );
}

