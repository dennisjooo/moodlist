'use client';

import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { motion } from '@/components/ui/lazy-motion';
import { CARD_FADE_IN_UP_VARIANTS, GRADIENT_SCALE_VARIANTS } from '@/lib/constants/animations';
import { cn } from '@/lib/utils';
import { cleanText } from '@/lib/utils/text';
import { Download, Edit, ExternalLink, Loader2, Music2, RefreshCw, Sparkles, Trash2, Shuffle } from 'lucide-react';

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
  onRemix: () => void;
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
  onRemix,
  colorScheme,
}: PlaylistStatusBannerProps) {
  return (
    <motion.div
      variants={CARD_FADE_IN_UP_VARIANTS}
      initial="hidden"
      animate="visible"
    >
      <Card className="relative overflow-hidden">
        {/* Subtle gradient background accent */}
        {colorScheme && (
          <motion.div
            className="absolute top-0 left-0 right-0 h-1 origin-left"
            style={{
              background: `linear-gradient(90deg, ${colorScheme.primary}, ${colorScheme.secondary}, ${colorScheme.tertiary})`
            }}
            variants={GRADIENT_SCALE_VARIANTS}
            initial="hidden"
            animate="visible"
          />
        )}

        <CardContent className="p-4 sm:p-6">
          <div className="flex flex-col sm:flex-row gap-4">
            {/* Left side: Icon + Info */}
            <div className="flex gap-3 sm:gap-4 flex-1 min-w-0">
              <div
                className={cn(
                  "w-16 h-16 sm:w-20 sm:h-20 rounded-xl flex items-center justify-center flex-shrink-0 shadow-md",
                  !colorScheme && (hasSavedToSpotify ? "bg-green-500" : "bg-orange-500")
                )}
                style={colorScheme ? {
                  background: `linear-gradient(135deg, ${colorScheme.primary}, ${colorScheme.secondary})`
                } : undefined}
              >
                <Music2 className="w-8 h-8 sm:w-10 sm:h-10 text-white" />
              </div>

              <div className="flex-1 min-w-0 flex flex-col justify-center">
                <h3 className="font-bold text-xl sm:text-2xl truncate mb-1">
                  {hasSavedToSpotify ? (playlistName || 'Saved Playlist') : 'Your Draft Playlist'}
                </h3>
                <div className="flex items-start gap-1.5 mb-1.5">
                  <Sparkles className="w-3.5 h-3.5 flex-shrink-0 mt-0.5 text-muted-foreground" />
                  <p className="text-sm text-muted-foreground flex-1">
                    {cleanText(moodPrompt)}
                  </p>
                </div>
                <div className="flex items-center gap-2 text-xs ml-5">
                  <span className="text-muted-foreground font-medium">{trackCount} {trackCount === 1 ? 'track' : 'tracks'}</span>
                  <span className="text-muted-foreground">•</span>
                  {hasSavedToSpotify ? (
                    <span className="text-green-600 dark:text-green-400 font-medium">Saved to Spotify</span>
                  ) : (
                    <span className="text-orange-600 dark:text-orange-400 font-medium">Draft</span>
                  )}
                </div>
              </div>
            </div>

            {/* Right side: Actions */}
            <div className="flex flex-col gap-2 sm:justify-center sm:min-w-[200px]">
              {/* Primary action */}
              {hasSavedToSpotify && spotifyUrl ? (
                <Button
                  asChild
                  size="lg"
                  className="w-full shadow-sm"
                >
                  <a
                    href={spotifyUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center justify-center gap-2"
                  >
                    <ExternalLink className="w-4 h-4" />
                    Open in Spotify
                  </a>
                </Button>
              ) : (
                <Button
                  onClick={onSaveToSpotify}
                  disabled={isSaving}
                  size="lg"
                  className="w-full shadow-sm"
                >
                  {isSaving ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin mr-2" />
                      Saving...
                    </>
                  ) : (
                    <>
                      <Download className="w-4 h-4 mr-2" />
                      Save to Spotify
                    </>
                  )}
                </Button>
              )}

              {/* Secondary actions row */}
              <div className="flex gap-2">
                {hasSavedToSpotify && (
                  <Button
                    variant="outline"
                    size="default"
                    onClick={onSyncFromSpotify}
                    disabled={isSyncing}
                    className="flex-1 gap-2"
                  >
                    <RefreshCw className={cn("w-4 h-4", isSyncing && "animate-spin")} />
                    <span className="hidden sm:inline">Sync</span>
                  </Button>
                )}

                <Button
                  variant="outline"
                  size="default"
                  onClick={onRemix}
                  className="flex-1 gap-2"
                >
                  <Shuffle className="w-4 h-4" />
                  <span className="hidden sm:inline">Remix</span>
                </Button>

                <Button
                  variant="outline"
                  size="default"
                  onClick={onEdit}
                  className="flex-1 gap-2"
                >
                  <Edit className="w-4 h-4" />
                  <span className="hidden sm:inline">Edit</span>
                </Button>

                <Button
                  variant="outline"
                  size="default"
                  onClick={onDelete}
                  disabled={isDeleting}
                  className="flex-1 gap-2 text-destructive hover:text-destructive hover:bg-destructive/10"
                >
                  <Trash2 className="w-4 h-4" />
                  <span className="hidden sm:inline">Delete</span>
                </Button>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}

