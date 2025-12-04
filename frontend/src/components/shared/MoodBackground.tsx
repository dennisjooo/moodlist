'use client';

import { useEffect, useState } from 'react';

interface ColorScheme {
    primary: string;
    secondary: string;
    tertiary: string;
}

interface MoodBackgroundProps {
    colorScheme?: ColorScheme;
    style?: 'radial' | 'linear-diagonal' | 'linear-vertical' | 'mesh' | 'orbs';
    opacity?: number;
}

export default function MoodBackground({
    colorScheme,
    style = 'linear-diagonal',
    opacity = 0.3
}: MoodBackgroundProps) {
    const [currentOpacity, setCurrentOpacity] = useState(0);

    useEffect(() => {
        if (colorScheme) {
            // Delay to ensure smooth transition without flash
            const timer = setTimeout(() => {
                setCurrentOpacity(opacity);
            }, 100);
            return () => clearTimeout(timer);
        } else {
            setCurrentOpacity(0);
        }
    }, [colorScheme, opacity]);

    if (!colorScheme) return null;

    const getGradientStyle = () => {
        switch (style) {
            case 'radial':
                return `radial-gradient(circle at center, ${colorScheme.primary} 0%, ${colorScheme.secondary} 35%, ${colorScheme.tertiary} 70%, transparent 100%)`;

            case 'linear-diagonal':
                return `linear-gradient(135deg, ${colorScheme.primary} 0%, ${colorScheme.secondary} 50%, ${colorScheme.tertiary} 100%)`;

            case 'linear-vertical':
                return `linear-gradient(180deg, ${colorScheme.primary} 0%, ${colorScheme.secondary} 50%, ${colorScheme.tertiary} 100%)`;

            case 'mesh':
                return `
          linear-gradient(135deg, ${colorScheme.primary}60 0%, transparent 50%),
          linear-gradient(225deg, ${colorScheme.secondary}60 0%, transparent 50%),
          linear-gradient(315deg, ${colorScheme.tertiary}60 0%, transparent 50%)
        `;

            case 'orbs':
                return `
          radial-gradient(circle at 20% 30%, ${colorScheme.primary} 0%, transparent 40%),
          radial-gradient(circle at 80% 20%, ${colorScheme.secondary} 0%, transparent 40%),
          radial-gradient(circle at 50% 80%, ${colorScheme.tertiary} 0%, transparent 40%)
        `;

            default:
                return `linear-gradient(135deg, ${colorScheme.primary} 0%, ${colorScheme.secondary} 50%, ${colorScheme.tertiary} 100%)`;
        }
    };

    return (
        <div
            className="fixed inset-0 z-0 transition-opacity duration-[1600ms] ease-[cubic-bezier(0.22,0.61,0.36,1)]"
            style={{
                background: getGradientStyle(),
                opacity: currentOpacity,
            }}
        />
    );
}
