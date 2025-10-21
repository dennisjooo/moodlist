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

interface DeletePlaylistDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  playlistName: string;
  isDeleting: boolean;
  onConfirm: () => void;
}

export default function DeletePlaylistDialog({
  open,
  onOpenChange,
  playlistName,
  isDeleting,
  onConfirm,
}: DeletePlaylistDialogProps) {
  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Delete Playlist</AlertDialogTitle>
          <AlertDialogDescription>
            Are you sure you want to delete &quot;{playlistName}&quot;?
            This action cannot be undone and will remove the playlist from both your account.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={isDeleting}>Cancel</AlertDialogCancel>
          <AlertDialogAction
            onClick={onConfirm}
            disabled={isDeleting}
            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
          >
            {isDeleting ? 'Deleting...' : 'Delete'}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}

