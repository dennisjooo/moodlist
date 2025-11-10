'use client';

import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { initiateSpotifyAuth } from '@/lib/spotifyAuth';
import { config } from '@/lib/config';
import { Info, ExternalLink } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface LimitedAccessDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
}

export function LimitedAccessDialog({ open, onOpenChange }: LimitedAccessDialogProps) {
    const handleProceed = () => {
        onOpenChange(false);
        initiateSpotifyAuth();
    };

    const { betaContactUrl, betaContactLabel } = config.access;

    return (
        <AlertDialog open={open} onOpenChange={onOpenChange}>
            <AlertDialogContent>
                <AlertDialogHeader>
                    <div className="flex items-center gap-2">
                        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10">
                            <Info className="h-5 w-5 text-primary" />
                        </div>
                        <AlertDialogTitle>Limited Beta Access</AlertDialogTitle>
                    </div>
                    <AlertDialogDescription className="text-left space-y-3 pt-2">
                        <p>
                            MoodList is currently in <strong>limited beta</strong>. Our Spotify API is in development mode, which means we can only support a small number of users right now (up to 25 manually whitelisted accounts).
                        </p>
                        <p>
                            If you&apos;ve already been added to our whitelist, you can proceed with login. Otherwise, you&apos;ll see an error from Spotify.
                        </p>
                        <div className="rounded-lg border border-border/60 bg-muted/30 p-3 text-sm space-y-2">
                            <p className="font-medium">Want access?</p>
                            <p className="text-muted-foreground">
                                We&apos;re working on getting full Spotify API approval. In the meantime, feel free to reach out if you&apos;d like to be added to the beta whitelist!
                            </p>
                            {betaContactUrl && (
                                <Button
                                    variant="outline"
                                    size="sm"
                                    asChild
                                    className="w-full mt-2"
                                >
                                    <a
                                        href={betaContactUrl}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="flex items-center justify-center gap-2"
                                    >
                                        {betaContactLabel || 'Request Access'}
                                        <ExternalLink className="h-3.5 w-3.5" />
                                    </a>
                                </Button>
                            )}
                        </div>
                    </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                    <AlertDialogCancel>Cancel</AlertDialogCancel>
                    <AlertDialogAction onClick={handleProceed}>
                        Proceed to Login
                    </AlertDialogAction>
                </AlertDialogFooter>
            </AlertDialogContent>
        </AlertDialog>
    );
}
