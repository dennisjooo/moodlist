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
import { Input } from '@/components/ui/input';
import { useState } from 'react';

interface RemixPlaylistDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  playlistName: string;
  originalMoodPrompt: string;
  isRemixing: boolean;
  onConfirm: (moodPrompt?: string) => void;
}

export default function RemixPlaylistDialog({
  open,
  onOpenChange,
  playlistName,
  originalMoodPrompt,
  isRemixing,
  onConfirm,
}: RemixPlaylistDialogProps) {
  const [moodPrompt, setMoodPrompt] = useState('');

  const handleConfirm = () => {
    // Combine original mood prompt with user's new direction
    const combinedPrompt = moodPrompt
      ? `${originalMoodPrompt}. ${moodPrompt}`
      : originalMoodPrompt;
    onConfirm(combinedPrompt);
  };

  const handleOpenChange = (open: boolean) => {
    onOpenChange(open);
    if (!open) {
      setMoodPrompt('');
    }
  };

  return (
    <AlertDialog open={open} onOpenChange={handleOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Remix Playlist</AlertDialogTitle>
          <AlertDialogDescription>
            Create a new version of &quot;{playlistName}&quot; based on your mood.
            The current tracks will be used as seeds.
            {originalMoodPrompt && (
              <>
                <br />
                <br />
                <span className="text-muted-foreground text-sm">
                  Original: &quot;{originalMoodPrompt}&quot;
                </span>
              </>
            )}
          </AlertDialogDescription>
        </AlertDialogHeader>
        <div className="grid gap-4 py-4">
          <div className="grid gap-2">
            <label htmlFor="mood-prompt" className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">
              Add modifications (Optional)
            </label>
            <Input
              id="mood-prompt"
              placeholder="e.g. Make it more energetic, add more jazz..."
              value={moodPrompt}
              onChange={(e) => setMoodPrompt(e.target.value)}
              disabled={isRemixing}
            />
          </div>
        </div>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={isRemixing}>Cancel</AlertDialogCancel>
          <AlertDialogAction
            onClick={(e) => {
              e.preventDefault();
              handleConfirm();
            }}
            disabled={isRemixing}
          >
            {isRemixing ? 'Starting Remix...' : 'Remix'}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
