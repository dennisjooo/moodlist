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
import { CARD_FADE_IN_UP_VARIANTS } from '@/lib/constants/animations';
import { cn } from '@/lib/utils';
import { cleanText } from '@/lib/utils/text';
import { ChevronDown, ChevronUp, Download, Edit, ExternalLink, Loader2, MoreHorizontal, Music2, RefreshCw, Shuffle, Sparkles, Trash2 } from 'lucide-react';
import { useState } from 'react';

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
  const [isExpanded, setIsExpanded] = useState(false);
  const fullTitle = hasSavedToSpotify ? (playlistName || 'Saved Playlist') : 'Your Draft Playlist';
  let title = fullTitle;
  let subtitle = '';

  if (fullTitle.includes(':')) {
    const splitIndex = fullTitle.indexOf(':');
    title = fullTitle.substring(0, splitIndex).trim();
    subtitle = fullTitle.substring(splitIndex + 1).trim();
  }

  const cleanedPrompt = cleanText(moodPrompt);
  const shouldTruncate = cleanedPrompt.length > 200;

  return (
    <motion.div
      variants={CARD_FADE_IN_UP_VARIANTS}
      initial="hidden"
      animate="visible"
      className="w-full"
    >
      <Card className="relative overflow-hidden border-0 shadow-lg">
        {/* Dynamic Gradient Background */}
        <div
          className="absolute inset-0 opacity-10 dark:opacity-20"
          style={colorScheme ? {
            background: `linear-gradient(135deg, ${colorScheme.primary}, ${colorScheme.secondary}, ${colorScheme.tertiary})`
          } : {
            background: 'linear-gradient(135deg, #3b82f6, #8b5cf6, #ec4899)'
          }}
        />

        {/* Glass effect overlay */}
        <div className="absolute inset-0 bg-background/60 backdrop-blur-sm" />

        <CardContent className="relative p-6 sm:p-8">
          <div className="flex flex-col md:flex-row gap-6 items-start">

            {/* Cover Art / Icon */}
            <div className="flex-shrink-0">
              <div
                className={cn(
                  "w-24 h-24 sm:w-32 sm:h-32 rounded-2xl flex items-center justify-center shadow-xl ring-1 ring-black/5 dark:ring-white/10",
                  !colorScheme && (hasSavedToSpotify ? "bg-green-500" : "bg-orange-500")
                )}
                style={colorScheme ? {
                  background: `linear-gradient(135deg, ${colorScheme.primary}, ${colorScheme.secondary})`
                } : undefined}
              >
                <Music2 className="w-12 h-12 sm:w-16 sm:h-16 text-white drop-shadow-md" />
              </div>
            </div>

            {/* Content Info */}
            <div className="flex-1 min-w-0 space-y-3">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  {hasSavedToSpotify ? (
                    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400">
                      Saved to Spotify
                    </span>
                  ) : (
                    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400">
                      Draft
                    </span>
                  )}
                  <span className="text-xs text-muted-foreground font-medium">•</span>
                  <span className="text-xs text-muted-foreground font-medium">{trackCount} tracks</span>
                </div>

                <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold tracking-tight truncate">
                  {title}
                </h2>
                {subtitle && (
                  <p className="text-lg sm:text-xl text-muted-foreground font-medium truncate mt-0.5">
                    {subtitle}
                  </p>
                )}
              </div>

              <div className="flex flex-col gap-1 max-w-2xl">
                <div className="flex items-start gap-2 text-sm text-muted-foreground bg-background/50 p-2.5 rounded-lg border border-border/50">
                  <Sparkles className="w-4 h-4 flex-shrink-0 mt-0.5 text-primary" />
                  <div className="flex-1">
                    <motion.div
                      initial={false}
                      animate={{ height: isExpanded || !shouldTruncate ? "auto" : "4.5rem" }}
                      className="overflow-hidden relative"
                    >
                      <p className="leading-relaxed">
                        {cleanedPrompt}
                      </p>
                      {shouldTruncate && !isExpanded && (
                        <div className="absolute bottom-0 left-0 right-0 h-6 bg-gradient-to-t from-background/10 to-transparent" />
                      )}
                    </motion.div>
                  </div>
                </div>
                {shouldTruncate && (
                  <button
                    onClick={() => setIsExpanded(!isExpanded)}
                    className="self-start text-xs font-medium text-muted-foreground hover:text-foreground flex items-center gap-1 ml-1 transition-colors"
                  >
                    {isExpanded ? (
                      <>
                        Show Less <ChevronUp className="w-3 h-3" />
                      </>
                    ) : (
                      <>
                        Show More <ChevronDown className="w-3 h-3" />
                      </>
                    )}
                  </button>
                )}
              </div>
            </div>

            {/* Actions */}
            <div className="flex flex-col gap-3 w-full md:w-auto md:min-w-[180px]">
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
                    <ExternalLink className="w-5 h-5" />
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
                      <Loader2 className="w-5 h-5 animate-spin mr-2" />
                      Saving...
                    </>
                  ) : (
                    <>
                      <Download className="w-5 h-5 mr-2" />
                      Save to Spotify
                    </>
                  )}
                </Button>
              )}

              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline" size="lg" className="h-12 w-full bg-background/80 backdrop-blur-sm hover:bg-accent/50">
                    <MoreHorizontal className="w-5 h-5 mr-2" />
                    <span>More Options</span>
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-56">
                  {hasSavedToSpotify && (
                    <DropdownMenuItem onClick={onSyncFromSpotify} disabled={isSyncing} className="cursor-pointer py-3">
                      <RefreshCw className={cn("w-4 h-4 mr-2", isSyncing && "animate-spin")} />
                      Sync from Spotify
                    </DropdownMenuItem>
                  )}
                  <DropdownMenuItem onClick={onRemix} className="cursor-pointer py-3">
                    <Shuffle className="w-4 h-4 mr-2" />
                    Remix Playlist
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={onEdit} className="cursor-pointer py-3">
                    <Edit className="w-4 h-4 mr-2" />
                    Edit Details
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    onClick={onDelete}
                    disabled={isDeleting}
                    className="text-destructive focus:text-destructive focus:bg-destructive/10 cursor-pointer py-3"
                  >
                    <Trash2 className="w-4 h-4 mr-2" />
                    Delete Playlist
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

