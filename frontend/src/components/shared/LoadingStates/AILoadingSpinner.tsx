'use client';

import { Sparkles } from 'lucide-react';

interface AILoadingSpinnerProps {
  title?: string;
  subtitle?: string;
}

/**
 * Loading spinner with animated musical notes for AI playlist creation
 */
export default function AILoadingSpinner({ 
  title = "Firing up the AI...",
  subtitle = "Preparing to analyze your vibe"
}: AILoadingSpinnerProps) {
  return (
    <div className="flex items-center justify-center min-h-[400px]">
      <div className="flex flex-col items-center gap-6">
        {/* Animated musical notes */}
        <div className="relative w-24 h-24">
          {/* Spinning ring */}
          <div className="absolute inset-0 rounded-full border-4 border-primary/20 animate-pulse"></div>
          <div className="absolute inset-0 rounded-full border-4 border-transparent border-t-primary animate-spin"></div>

          {/* Center icon */}
          <div className="absolute inset-0 flex items-center justify-center">
            <Sparkles className="w-8 h-8 text-primary animate-pulse" />
          </div>

          {/* Floating musical notes */}
          <div className="absolute -top-2 -right-2 w-6 h-6 bg-primary/20 rounded-full flex items-center justify-center animate-bounce" style={{ animationDelay: '0s', animationDuration: '2s' }}>
            <span className="text-xs">♪</span>
          </div>
          <div className="absolute -bottom-2 -left-2 w-5 h-5 bg-primary/20 rounded-full flex items-center justify-center animate-bounce" style={{ animationDelay: '0.5s', animationDuration: '2.5s' }}>
            <span className="text-xs">♫</span>
          </div>
          <div className="absolute top-1/2 -right-4 w-4 h-4 bg-primary/20 rounded-full flex items-center justify-center animate-bounce" style={{ animationDelay: '1s', animationDuration: '2s' }}>
            <span className="text-xs">♪</span>
          </div>
        </div>

        {/* Loading text with gradient */}
        <div className="text-center space-y-2">
          <p className="text-lg font-semibold bg-gradient-to-r from-primary to-primary/60 bg-clip-text text-transparent animate-pulse">
            {title}
          </p>
          <p className="text-sm text-muted-foreground">
            {subtitle}
          </p>
        </div>
      </div>
    </div>
  );
}

