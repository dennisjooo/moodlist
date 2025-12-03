'use client';

import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { motion } from '@/components/ui/lazy-motion';
import { CARD_FADE_IN_UP_VARIANTS, GRADIENT_SCALE_VARIANTS } from '@/lib/constants/animations';
import { cn } from '@/lib/utils';
import { cleanText } from '@/lib/utils/text';
import { Download, Edit, ExternalLink, Loader2, Music2, RefreshCw, Shuffle, Sparkles, Trash2 } from 'lucide-react';

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
  const fullTitle = hasSavedToSpotify ? (playlistName || 'Saved Playlist') : 'Your Draft Playlist';
  let title = fullTitle;
  let subtitle = '';

  if (fullTitle.includes(':')) {
    const splitIndex = fullTitle.indexOf(':');
    title = fullTitle.substring(0, splitIndex).trim();
    subtitle = fullTitle.substring(splitIndex + 1).trim();
  }

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
                <div className="flex flex-col mb-1">
                  <h3 className="font-bold text-xl sm:text-2xl truncate">
                    {title}
                  </h3>
                  {subtitle && (
                    <p className="text-base sm:text-lg text-muted-foreground truncate font-medium">
                      {subtitle}
                    </p>
                  )}
                </div>
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

              {/* Secondary actions dropdown */}
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline" size="icon" className="w-full">
                    <span>More Options</span>
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-64 sm:w">
                  {hasSavedToSpotify && (
                    <DropdownMenuItem onClick={onSyncFromSpotify} disabled={isSyncing} className="py-3 sm:py-1.5 cursor-pointer">
                      <RefreshCw className={cn("w-4 h-4 mr-2", isSyncing && "animate-spin")} />
                      Sync from Spotify
                    </DropdownMenuItem>
                  )}
                  <DropdownMenuItem onClick={onRemix} className="py-3 sm:py-1.5 cursor-pointer">
                    <Shuffle className="w-4 h-4 mr-2" />
                    Create a Remix
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={onEdit} className="py-3 sm:py-1.5 cursor-pointer">
                    <Edit className="w-4 h-4 mr-2" />
                    Edit
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    onClick={onDelete}
                    disabled={isDeleting}
                    className="text-destructive focus:text-destructive focus:bg-destructive/10 py-3 sm:py-1.5 cursor-pointer"
                  >
                    <Trash2 className="w-4 h-4 mr-2" />
                    Delete
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}

