'use client';

import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import { Download, Edit, ExternalLink, Loader2, Music, RefreshCw, Trash2 } from 'lucide-react';

interface PlaylistStatusBannerProps {
  hasSavedToSpotify: boolean;
  playlistName?: string;
  moodPrompt: string;
  trackCount: number;
  spotifyUrl?: string;
  isSaving: boolean;
  isSyncing: boolean;
  isDeleting: boolean;
  onSaveToSpotify: () => void;
  onSyncFromSpotify: () => void;
  onEdit: () => void;
  onDelete: () => void;
  colorScheme?: {
    primary: string;
    secondary: string;
    tertiary: string;
  };
}

export default function PlaylistStatusBanner({
  hasSavedToSpotify,
  playlistName,
  moodPrompt,
  trackCount,
  spotifyUrl,
  isSaving,
  isSyncing,
  isDeleting,
  onSaveToSpotify,
  onSyncFromSpotify,
  onEdit,
  onDelete,
  colorScheme,
}: PlaylistStatusBannerProps) {
  // Use color scheme if available, otherwise use default colors
  const iconStyle = colorScheme
    ? { background: `linear-gradient(135deg, ${colorScheme.primary}, ${colorScheme.secondary})` }
    : undefined;

  return (
    <Card className={cn(
      "border-2",
      hasSavedToSpotify ? "border-green-500 bg-green-50 dark:bg-green-950/20" : "border-yellow-500 bg-yellow-50 dark:bg-yellow-950/20"
    )}>
      <CardContent>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4 pr-3">
            <div
              className={cn(
                "w-12 h-12 rounded-full flex items-center justify-center flex-shrink-0",
                !colorScheme && (hasSavedToSpotify ? "bg-green-500" : "bg-yellow-500")
              )}
              style={iconStyle}
            >
              <Music className="w-6 h-6 text-white" />
            </div>
            <div>
              <h3 className="font-semibold text-xl">{hasSavedToSpotify ? (playlistName || 'Saved Playlist') : 'Your Draft Playlist'}</h3>
              <p className="text-sm text-muted-foreground mt-0.5">
                {hasSavedToSpotify ? '✅ Saved to Spotify' : '📝 Based on'} &quot;{moodPrompt}&quot; • {trackCount} tracks
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {hasSavedToSpotify ? (
              <>
                <Button
                  variant="outline"
                  onClick={onSyncFromSpotify}
                  size="lg"
                  disabled={isSyncing}
                  className="p-2"
                  title="Sync from Spotify"
                >
                  <RefreshCw className={cn("w-4 h-4", isSyncing && "animate-spin")} />
                </Button>
                <Button
                  variant="outline"
                  onClick={onEdit}
                  size="lg"
                  className="p-2"
                >
                  <Edit className="w-4 h-4" />
                </Button>
                <Button
                  variant="destructive"
                  onClick={onDelete}
                  size="lg"
                  disabled={isDeleting}
                  className="p-2"
                >
                  <Trash2 className="w-4 h-4" />
                </Button>
                {spotifyUrl && (
                  <Button asChild size="lg">
                    <a
                      href={spotifyUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-2"
                    >
                      <ExternalLink className="w-4 h-4" />
                      Open in Spotify
                    </a>
                  </Button>
                )}
              </>
            ) : (
              <>
                <Button
                  variant="outline"
                  onClick={onEdit}
                  size="lg"
                  className="p-2"
                >
                  <Edit className="w-4 h-4" />
                </Button>
                <Button
                  variant="destructive"
                  onClick={onDelete}
                  size="lg"
                  disabled={isDeleting}
                  className="p-2"
                >
                  <Trash2 className="w-4 h-4" />
                </Button>
                <Button
                  onClick={onSaveToSpotify}
                  disabled={isSaving}
                  size="lg"
                  className="flex items-center gap-2"
                >
                  {isSaving ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Saving...
                    </>
                  ) : (
                    <>
                      <Download className="w-4 h-4" />
                      Save to Spotify
                    </>
                  )}
                </Button>
              </>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

