'use client';

import { SpotifyLoginButton } from '@/components/features/auth/SpotifyLoginButton';
import {
    AlertDialog,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from '@/components/ui/alert-dialog';

interface LoginRequiredDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
}

export default function LoginRequiredDialog({ open, onOpenChange }: LoginRequiredDialogProps) {
    return (
        <AlertDialog open={open} onOpenChange={onOpenChange}>
            <AlertDialogContent>
                <AlertDialogHeader>
                    <AlertDialogTitle>Login Required</AlertDialogTitle>
                    <AlertDialogDescription>
                        Hold on there, buddy! We need you to log in to create playlists.
                        <br />
                        Mind logging in to your Spotify account to continue.
                    </AlertDialogDescription>
                </AlertDialogHeader>
                <div className="flex justify-center py-4">
                    <SpotifyLoginButton />
                </div>
                <AlertDialogFooter>
                    <AlertDialogCancel>Maybe later</AlertDialogCancel>
                </AlertDialogFooter>
            </AlertDialogContent>
        </AlertDialog>
    );
}

