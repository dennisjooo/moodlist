"use client";

import React from 'react';
import { cn } from '@/lib/utils';

export type LoadingSize = 'xs' | 'sm' | 'md' | 'lg';
export type LoadingVariant = 'spinner' | 'dots' | 'pulse';

interface LoadingProps {
  size?: LoadingSize;
  variant?: LoadingVariant;
  className?: string;
}

const sizeMap: Record<LoadingSize, number> = {
  xs: 12,
  sm: 16,
  md: 24,
  lg: 32,
};

export function Loading({ size = 'md', variant = 'dots', className }: LoadingProps) {
  const px = sizeMap[size];

  if (variant === 'spinner') {
    return (
      <div
        className={cn('inline-block rounded-full border-2 border-primary/20 border-t-primary animate-spin', className)}
        style={{ width: px, height: px }}
        aria-label="Loading"
      />
    );
  }

  if (variant === 'pulse') {
    return (
      <div
        className={cn('inline-block rounded-lg bg-primary/20 animate-pulse', className)}
        style={{ width: px, height: px }}
        aria-label="Loading"
      />
    );
  }

  // dots
  return (
    <div className={cn('inline-flex items-center gap-1', className)} aria-label="Loading">
      <span className="rounded-full bg-primary inline-block animate-bounce" style={{ width: px / 4, height: px / 4 }} />
      <span className="rounded-full bg-primary inline-block animate-bounce" style={{ width: px / 4, height: px / 4, animationDelay: '0.1s' }} />
      <span className="rounded-full bg-primary inline-block animate-bounce" style={{ width: px / 4, height: px / 4, animationDelay: '0.2s' }} />
    </div>
  );
}
