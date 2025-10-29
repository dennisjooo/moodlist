import { useCallback } from 'react';

interface ColorScheme {
    primary: string;
    secondary: string;
    tertiary: string;
}

interface BadgeStyling {
    style: React.CSSProperties;
    onMouseEnter: (e: React.MouseEvent<HTMLElement>) => void;
    onMouseLeave: (e: React.MouseEvent<HTMLElement>) => void;
    className: string;
}

export function useMoodAnalysisStyling(colorScheme?: ColorScheme) {
    // Helper function to brighten dark colors
    const brightenColor = useCallback((color: string, amount: number = 0.3): string => {
        if (!color || !color.startsWith('#')) return color;

        const hex = color.replace('#', '');
        const r = parseInt(hex.slice(0, 2), 16);
        const g = parseInt(hex.slice(2, 4), 16);
        const b = parseInt(hex.slice(4, 6), 16);

        const brightenedR = Math.min(255, Math.round(r + (255 - r) * amount));
        const brightenedG = Math.min(255, Math.round(g + (255 - g) * amount));
        const brightenedB = Math.min(255, Math.round(b + (255 - b) * amount));

        return `#${brightenedR.toString(16).padStart(2, '0')}${brightenedG.toString(16).padStart(2, '0')}${brightenedB.toString(16).padStart(2, '0')}`;
    }, []);

    // Helper function to add glow effect on hover
    const addGlowEffect = useCallback((color: string, intensity: string = '20px') => {
        return `0 0 ${intensity} ${color}40`;
    }, []);

    // Create hover event handlers
    const createHoverHandlers = useCallback((
        color: string,
        intensity: string = '20px',
        backgroundEffect?: boolean
    ) => ({
        onMouseEnter: (e: React.MouseEvent<HTMLElement>) => {
            if (colorScheme) {
                const brightenedColor = brightenColor(color, 0.1);
                e.currentTarget.style.boxShadow = addGlowEffect(brightenedColor, intensity);
                if (backgroundEffect) {
                    e.currentTarget.style.backgroundColor = `${brightenColor(color, 0.3)}15`;
                }
            }
        },
        onMouseLeave: (e: React.MouseEvent<HTMLElement>) => {
            if (colorScheme) {
                e.currentTarget.style.boxShadow = '0 0 0 rgba(0,0,0,0)';
                if (backgroundEffect) {
                    e.currentTarget.style.backgroundColor = 'transparent';
                }
            }
        }
    }), [colorScheme, brightenColor, addGlowEffect]);

    // Generate styling for primary emotion badge
    const getPrimaryBadgeStyling = useCallback((): BadgeStyling => {
        if (!colorScheme) {
            return {
                style: {},
                onMouseEnter: () => { },
                onMouseLeave: () => { },
                className: 'capitalize transition-all duration-300 hover:scale-105 hover:shadow-lg'
            };
        }

        return {
            style: {
                backgroundColor: `${brightenColor(colorScheme.primary, 0.4)}40`,
                color: brightenColor(colorScheme.primary, 0.2),
                borderColor: brightenColor(colorScheme.primary, 0.1),
                boxShadow: '0 0 0 rgba(0,0,0,0)'
            },
            className: 'capitalize transition-all duration-300 hover:scale-105 hover:shadow-lg',
            ...createHoverHandlers(colorScheme.primary, '20px')
        };
    }, [colorScheme, brightenColor, createHoverHandlers]);

    // Generate styling for secondary badge (energy level)
    const getSecondaryBadgeStyling = useCallback((): BadgeStyling => {
        if (!colorScheme) {
            return {
                style: {},
                onMouseEnter: () => { },
                onMouseLeave: () => { },
                className: 'capitalize transition-all duration-300 hover:scale-105 hover:shadow-lg'
            };
        }

        return {
            style: {
                backgroundColor: `${brightenColor(colorScheme.secondary, 0.4)}40`,
                color: brightenColor(colorScheme.secondary, 0.2),
                borderColor: brightenColor(colorScheme.secondary, 0.1),
                boxShadow: '0 0 0 rgba(0,0,0,0)'
            },
            className: 'capitalize transition-all duration-300 hover:scale-105 hover:shadow-lg',
            ...createHoverHandlers(colorScheme.secondary, '20px')
        };
    }, [colorScheme, brightenColor, createHoverHandlers]);

    // Generate styling for keyword badges
    const getKeywordBadgeStyling = useCallback((): BadgeStyling => {
        if (!colorScheme) {
            return {
                style: {},
                onMouseEnter: () => { },
                onMouseLeave: () => { },
                className: 'capitalize transition-all duration-300 hover:scale-105 hover:shadow-lg'
            };
        }

        return {
            style: {
                borderColor: brightenColor(colorScheme.tertiary, 0.2),
                color: brightenColor(colorScheme.tertiary, 0.1),
                boxShadow: '0 0 0 rgba(0,0,0,0)'
            },
            className: 'capitalize transition-all duration-300 hover:scale-105 hover:shadow-lg',
            ...createHoverHandlers(colorScheme.tertiary, '15px', true)
        };
    }, [colorScheme, brightenColor, createHoverHandlers]);

    return {
        getPrimaryBadgeStyling,
        getSecondaryBadgeStyling,
        getKeywordBadgeStyling,
        brightenColor,
        primaryBadgeProps: getPrimaryBadgeStyling(),
        secondaryBadgeProps: getSecondaryBadgeStyling(),
        getKeywordBadgeProps: () => getKeywordBadgeStyling()
    };
}
