'use client';

import { Button } from '@/components/ui/button';

interface SessionActionsProps {
    status: string | null;
    hasPlaylist: boolean;
    onRetry: () => void;
    onStartNew: () => void;
}

export function SessionActions({
    status,
    hasPlaylist,
    onRetry,
    onStartNew,
}: SessionActionsProps) {
    if (status === 'completed' && hasPlaylist) {
        return (
            <div className="pt-2 border-t border-border/40">
                <Button
                    variant="outline"
                    onClick={onStartNew}
                    className="w-full bg-gradient-to-r from-primary/5 to-primary/10 hover:from-primary/10 hover:to-primary/20 border-primary/20 hover:border-primary/30 transition-all"
                >
                    Start New Playlist
                </Button>
            </div>
        );
    }

    if (status === 'failed') {
        return (
            <div className="flex gap-3 pt-2 border-t border-border/40">
                <Button
                    onClick={onRetry}
                    className="flex-1 bg-gradient-to-r from-primary to-primary/90 hover:from-primary/90 hover:to-primary shadow-sm"
                >
                    Try Again
                </Button>
                <Button
                    variant="outline"
                    onClick={onStartNew}
                    className="hover:bg-muted/50 transition-colors"
                >
                    Cancel
                </Button>
            </div>
        );
    }

    return null;
}
