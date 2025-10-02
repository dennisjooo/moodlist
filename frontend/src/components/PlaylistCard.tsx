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
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { generateMoodGradient } from '@/lib/moodColors';
import { Calendar, ExternalLink, Music, Play, Trash2 } from 'lucide-react';
import Link from 'next/link';
import { useState } from 'react';

interface PlaylistCardProps {
  mood: string;
  title: string;
  createdAt: string;
  trackCount: number;
  spotifyUrl: string;
  sessionId?: string;
  status?: string;
  playlistId?: number;
  onDelete?: (playlistId: number) => void;
}

export default function PlaylistCard({ mood, title, createdAt, trackCount, spotifyUrl, sessionId, status, playlistId, onDelete }: PlaylistCardProps) {
  const autoGradient = generateMoodGradient(mood);
  const isCompleted = status === 'completed';
  const [isDeleting, setIsDeleting] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);

  const handleDeleteClick = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setShowDeleteDialog(true);
  };

  const handleConfirmDelete = async () => {
    if (!playlistId || !onDelete) return;

    setIsDeleting(true);
    try {
      await onDelete(playlistId);
      setShowDeleteDialog(false);
    } catch (error) {
      console.error('Failed to delete:', error);
      setIsDeleting(false);
    }
  };

  return (
    <>
      <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Playlist</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete "{title}"? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isDeleting}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleConfirmDelete}
              disabled={isDeleting}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {isDeleting ? 'Deleting...' : 'Delete'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <div className="group cursor-pointer transition-all duration-300 hover:scale-105 hover:shadow-xl rounded-lg overflow-hidden">
        {/* Full Gradient Background */}
        <div className={`${autoGradient} h-64 flex flex-col justify-between p-6 relative`}>
          <div className="absolute inset-0 bg-black/10 group-hover:bg-black/5 transition-colors" />

          {/* Header */}
          <div className="relative z-10 flex items-center justify-between">
            <div className="w-10 h-10 bg-white/20 backdrop-blur-sm rounded-full flex items-center justify-center">
              <Music className="w-5 h-5 text-white" />
            </div>
            <div className="flex items-center gap-2">
              <Badge className="bg-white/20 backdrop-blur-sm text-white border-white/30 hover:bg-white/30">
                {trackCount} tracks
              </Badge>
              {playlistId && onDelete && (
                <Button
                  size="sm"
                  variant="ghost"
                  className="h-6 w-8 p-0 bg-white/10 backdrop-blur-sm hover:bg-red-500/80 text-white"
                  onClick={handleDeleteClick}
                  disabled={isDeleting}
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </Button>
              )}
            </div>
          </div>

          {/* Content */}
          <div className="relative z-10 space-y-3">
            <div>
              <h3 className="font-bold text-white text-lg mb-1 drop-shadow-sm">{title}</h3>
              <p className="text-sm text-white/90 drop-shadow-sm">"{mood}"</p>
            </div>

            <div className="flex items-center text-sm text-white/80 mb-4">
              <Calendar className="w-4 h-4 mr-2" />
              Created {new Date(createdAt).toLocaleDateString()}
            </div>

            <div className="flex gap-2">
              {sessionId && (
                <Link href={`/create/${sessionId}`} className="flex-1">
                  <Button
                    size="sm"
                    className="w-full bg-white/20 backdrop-blur-sm hover:bg-white/30 text-white border-white/30"
                    variant="outline"
                  >
                    <Play className="w-4 h-4 mr-2" />
                    {isCompleted ? 'View' : 'Continue'}
                  </Button>
                </Link>
              )}
              {spotifyUrl && spotifyUrl !== '#' && (
                <a href={spotifyUrl} target="_blank" rel="noopener noreferrer">
                  <Button
                    size="sm"
                    className="bg-white/20 backdrop-blur-sm hover:bg-white/30 text-white border-white/30"
                    variant="outline"
                  >
                    <ExternalLink className="w-4 h-4" />
                  </Button>
                </a>
              )}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}