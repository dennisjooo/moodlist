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
import { Button } from '@/components/ui/button';
import { config } from '@/lib/config';
import { initiateSpotifyAuth } from '@/lib/spotifyAuth';
import { ExternalLink, Info } from 'lucide-react';

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
                    <AlertDialogDescription asChild>
                        <div className="text-left space-y-3 pt-2">
                            <div>
                                MoodList is currently in <strong>limited beta</strong>. Our Spotify API is in development mode, which means we can only support a small number of users right now (up to 25 manually whitelisted accounts).
                            </div>
                            <div>
                                If you&apos;ve already been added to our whitelist, you can proceed with login. Otherwise, you&apos;ll see an error from Spotify.
                            </div>
                            <div className="rounded-lg border border-border/60 bg-muted/30 p-3 text-sm space-y-2">
                                <div className="font-medium">Want access?</div>
                                <div className="text-muted-foreground">
                                    We currently don&apos; have a restriction from Spotify to 25 users. If you're interested in being added to the beta whitelist, please reach out to us.
                                </div>
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
