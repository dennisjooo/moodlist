"use client";

import { cn } from "@/lib/utils";

interface LoadingDotsProps {
  size?: "sm" | "md" | "lg";
  className?: string;
  containerClassName?: string;
}

export function LoadingDots({
  size = "sm",
  className,
  containerClassName
}: LoadingDotsProps) {
  const sizeClasses = {
    sm: "w-3 h-3",
    md: "w-4 h-4",
    lg: "w-5 h-5"
  };

  const dotClass = sizeClasses[size];

  return (
    <div className={cn("flex items-center justify-center space-x-2", containerClassName)}>
      <div className={cn(dotClass, "bg-primary rounded-full animate-bounce", className)}></div>
      <div className={cn(dotClass, "bg-primary rounded-full animate-bounce", className)} style={{ animationDelay: '0.1s' }}></div>
      <div className={cn(dotClass, "bg-primary rounded-full animate-bounce", className)} style={{ animationDelay: '0.2s' }}></div>
    </div>
  );
}