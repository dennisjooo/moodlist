'use client';

import { initiateSpotifyAuth, isSpotifyAuthConfigured } from '@/lib/spotifyAuth';
import { config } from '@/lib/config';
import { LimitedAccessDialog } from './LimitedAccessDialog';
import { useState, type ButtonHTMLAttributes, type MouseEvent, type ReactNode } from 'react';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { Info } from 'lucide-react';

interface SpotifyLoginButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
    children?: ReactNode;
    showTooltip?: boolean;
}

export function SpotifyLoginButton({ className, children, showTooltip = true, onClick, ...rest }: SpotifyLoginButtonProps) {
    const [dialogOpen, setDialogOpen] = useState(false);
    const showLimitedAccess = config.access.isDevMode && config.access.showLimitedAccessNotice;

    const handleClick = async (event: MouseEvent<HTMLButtonElement>) => {
        onClick?.(event);

        if (event.isDefaultPrevented()) {
            return;
        }

        if (!isSpotifyAuthConfigured()) {
            return;
        }

        if (showLimitedAccess) {
            event.preventDefault();
            setDialogOpen(true);
        } else {
            await initiateSpotifyAuth();
        }
    };

    const button = (
        <button
            {...rest}
            type={rest.type ?? 'button'}
            data-spotify-login
            onClick={handleClick}
            className={className || "bg-[#1DB954] hover:bg-[#1ed760] text-white h-10 px-6 rounded-md font-medium transition-all duration-200 flex items-center gap-2 shadow-md hover:shadow-lg"}
        >
            <svg
                className="w-4 h-4"
                viewBox="0 0 24 24"
                fill="currentColor"
                xmlns="http://www.w3.org/2000/svg"
            >
                <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.42 1.56-.299.421-1.02.599-1.559.3z" />
            </svg>
            {children || 'Login'}
            {showLimitedAccess && (
                <Info className="w-3.5 h-3.5 ml-0.5 opacity-80" />
            )}
        </button>
    );

    return (
        <>
            {showLimitedAccess && showTooltip ? (
                <TooltipProvider>
                    <Tooltip delayDuration={300}>
                        <TooltipTrigger asChild>
                            {button}
                        </TooltipTrigger>
                        <TooltipContent side="bottom" className="max-w-[240px]">
                            <p className="text-xs">Limited beta - whitelisted users only</p>
                        </TooltipContent>
                    </Tooltip>
                </TooltipProvider>
            ) : (
                button
            )}
            {showLimitedAccess && <LimitedAccessDialog open={dialogOpen} onOpenChange={setDialogOpen} />}
        </>
    );
}
