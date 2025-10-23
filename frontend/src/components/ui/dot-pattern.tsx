"use client";

import { cn } from "@/lib/utils";
import { useId } from "react";
import type { SVGProps } from "react";

/**
 *  DotPattern Component Props
 *
 * @param {number} [width=16] - The horizontal spacing between dots
 * @param {number} [height=16] - The vertical spacing between dots
 * @param {number} [cx=1] - The x-offset of individual dots
 * @param {number} [cy=1] - The y-offset of individual dots
 * @param {number} [cr=1] - The radius of each dot
 * @param {string} [className] - Additional CSS classes to apply to the SVG container
 * @param {boolean} [glow=false] - Whether dots should have a glowing effect
 */
interface DotPatternProps extends SVGProps<SVGSVGElement> {
  width?: number;
  height?: number;
  cx?: number;
  cy?: number;
  cr?: number;
  className?: string;
  glow?: boolean;
}

/**
 * DotPattern Component
 *
 * Lightweight SVG dot pattern background that avoids expensive per-dot animations.
 */
export function DotPattern({
  width = 16,
  height = 16,
  cx = 1,
  cy = 1,
  cr = 1,
  className,
  glow = false,
  ...props
}: DotPatternProps) {
  const patternId = useId();
  const gradientId = `${patternId}-gradient`;

  return (
    <svg
      aria-hidden="true"
      className={cn(
        "pointer-events-none absolute inset-0 h-full w-full text-neutral-400/60",
        className,
      )}
      role="presentation"
      {...props}
    >
      <defs>
        {glow ? (
          <>
            <radialGradient id={gradientId}>
              <stop offset="0%" stopColor="currentColor" stopOpacity="0.45" />
              <stop offset="100%" stopColor="currentColor" stopOpacity="0" />
            </radialGradient>
            <pattern
              id={patternId}
              width={width}
              height={height}
              patternUnits="userSpaceOnUse"
            >
              <circle cx={cx} cy={cy} r={cr} fill={`url(#${gradientId})`} />
            </pattern>
          </>
        ) : (
          <pattern
            id={patternId}
            width={width}
            height={height}
            patternUnits="userSpaceOnUse"
          >
            <circle cx={cx} cy={cy} r={cr} fill="currentColor" />
          </pattern>
        )}
      </defs>

      <rect width="100%" height="100%" fill={`url(#${patternId})`} />
    </svg>
  );
}
