'use client';

import { AnimatedThemeToggler } from '@/components/ui/animated-theme-toggler';
import { useTheme } from 'next-themes';

export function ThemeToggle() {
  const { setTheme, theme } = useTheme();

  return (
    <AnimatedThemeToggler
      className="h-8 w-8 p-0 bg-transparent hover:bg-transparent border-0"
      onToggle={() => setTheme(theme === 'light' ? 'dark' : 'light')}
    />
  );
}