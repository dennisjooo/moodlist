import { useMemo } from 'react';
import { usePlaylistFormatting } from '@/lib/hooks';
import { generateMoodGradient } from '@/lib/moodColors';
import { GradientStyle } from './types';

interface UsePlaylistCardGradientProps {
  mood: string;
  colorPrimary?: string;
  colorSecondary?: string;
  colorTertiary?: string;
}

export function usePlaylistCardGradient({
  mood,
  colorPrimary,
  colorSecondary,
  colorTertiary,
}: UsePlaylistCardGradientProps): GradientStyle {
  const { generateModernGradient } = usePlaylistFormatting();

  return useMemo(() => {
    const hasLLMColors = colorPrimary && colorSecondary && colorTertiary;

    if (hasLLMColors) {
      return {
        style: generateModernGradient(colorPrimary, colorSecondary, colorTertiary),
      };
    }

    return {
      className: generateMoodGradient(mood),
    };
  }, [mood, colorPrimary, colorSecondary, colorTertiary, generateModernGradient]);
}

