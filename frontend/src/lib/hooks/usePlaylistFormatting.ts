import { useMemo } from 'react';

export interface PlaylistFormattingOptions {
    primary: string;
    secondary: string;
    tertiary: string;
}

/**
 * Hook for playlist card formatting utilities
 * Provides gradient generation and text cleaning functions
 */
export function usePlaylistFormatting() {
    // Clean text by removing special characters and unwanted content
    const cleanText = useMemo(() => {
        return (text: string): string => {
            return text
                .replace(/\n/g, ' ') // Remove newlines
                .replace(/\r/g, ' ') // Remove carriage returns
                .replace(/\t/g, ' ') // Remove tabs
                .replace(/\s+/g, ' ') // Normalize multiple spaces
                .replace(/[^\w\s\-.,!?']/g, '') // Remove special characters but keep basic punctuation
                .trim();
        };
    }, []);

    // Generate modern blend gradient exactly matching cover_image_generator.py's algorithm
    const generateModernGradient = useMemo(() => {
        return (primary: string, secondary: string, tertiary: string) => {
            return {
                background: `
          /* Primary diagonal influence (diag1 + vert): top-left to bottom-right */
          radial-gradient(ellipse 160% 120% at 20% 20%, ${primary} 0%, transparent 75%),
          /* Secondary diagonal influence (diag2 + horiz): top-right to bottom-left */
          radial-gradient(ellipse 140% 100% at 80% 30%, ${secondary} 0%, transparent 70%),
          /* Tertiary center-bottom influence */
          radial-gradient(ellipse 120% 140% at 50% 70%, ${tertiary} 0%, transparent 65%),
          /* Main diagonal blend (135deg) - matches Python's diag1 flow */
          linear-gradient(135deg, ${primary} 0%, ${secondary} 35%, ${tertiary} 65%, ${primary} 100%),
          /* Cross diagonal blend (45deg) - matches Python's diag2 flow */
          linear-gradient(45deg, ${secondary} 0%, ${tertiary} 40%, ${primary} 75%)
        `,
                backgroundBlendMode: 'normal, normal, normal, multiply, overlay',
                backgroundSize: '100% 100%',
                backgroundRepeat: 'no-repeat'
            } as const;
        };
    }, []);

    return {
        cleanText,
        generateModernGradient,
    };
}
