"use client";

import { DeletePlaylistDialog } from '@/components/features/playlist/PlaylistCard/DeletePlaylistDialog';
import { usePlaylistCardDelete } from '@/components/features/playlist/PlaylistCard/usePlaylistCardDelete';
import { usePlaylistCardGradient } from '@/components/features/playlist/PlaylistCard/usePlaylistCardGradient';
import { Button } from '@/components/ui/button';
import { UserPlaylist } from '@/lib/api/playlist';
import { cn } from '@/lib/utils';
import { cleanText } from '@/lib/utils/text';
import { CalendarDays, Edit, ExternalLink, Music, Play, Trash2 } from 'lucide-react';
import Link from 'next/link';

interface PlaylistListItemProps {
    playlist: UserPlaylist;
    onDelete: (playlistId: number) => Promise<void>;
    formatDate: (dateString: string) => string;
}

export function PlaylistListItem({ playlist, onDelete, formatDate }: PlaylistListItemProps) {
    const gradient = usePlaylistCardGradient({
        mood: playlist.mood_prompt,
        colorPrimary: playlist.color_primary,
        colorSecondary: playlist.color_secondary,
        colorTertiary: playlist.color_tertiary,
    });

    const {
        isDeleting,
        showDeleteDialog,
        setShowDeleteDialog,
        handleDeleteClick,
        handleConfirmDelete,
    } = usePlaylistCardDelete({ playlistId: playlist.id, onDelete });

    const isCompleted = playlist.status === 'completed';
    const displayTitle = cleanText(playlist.name || playlist.mood_prompt);
    const displayMood = cleanText(playlist.mood_analysis_data?.mood_interpretation || playlist.mood_prompt);
    const hasSpotifyUrl = Boolean(playlist.spotify_url && playlist.spotify_url !== '#');
    const trackLabel = `${playlist.track_count} ${playlist.track_count === 1 ? 'track' : 'tracks'}`;

    return (
        <>
            <DeletePlaylistDialog
                open={showDeleteDialog}
                onOpenChange={setShowDeleteDialog}
                onConfirm={handleConfirmDelete}
                playlistTitle={displayTitle}
                isDeleting={isDeleting}
            />

            <div className="group relative overflow-hidden rounded-2xl border border-border/40 bg-card/50 backdrop-blur-sm shadow-sm transition-all duration-300 hover:border-primary/50 hover:shadow-2xl hover:bg-card/80">
                <div className="flex flex-col gap-4 p-4 sm:gap-5 sm:p-5 md:flex-row md:items-center md:justify-between md:gap-6 md:p-6">
                    {/* Left side - Content */}
                    <div className="flex min-w-0 flex-1 items-start gap-3 sm:gap-4 md:gap-5">
                        {/* Thumbnail */}
                        <div className="relative h-16 w-16 shrink-0 overflow-hidden rounded-xl shadow-lg ring-1 ring-black/10 transition-all duration-300 group-hover:shadow-xl group-hover:ring-primary/20 sm:h-20 sm:w-20 sm:rounded-2xl md:h-24 md:w-24">
                            <div
                                className={cn('h-full w-full transition-transform duration-500 ease-out group-hover:scale-110', gradient.className)}
                                style={gradient.style}
                            />
                            <div className="absolute inset-0 bg-gradient-to-br from-white/10 via-transparent to-black/5" />
                        </div>

                        {/* Text content */}
                        <div className="min-w-0 flex-1 space-y-2 sm:space-y-2.5 md:space-y-3 md:pt-1">
                            <div>
                                <h3 className="text-base font-bold leading-tight tracking-tight text-foreground mb-1.5 group-hover:text-primary transition-colors sm:text-lg md:text-xl sm:mb-2">
                                    {displayTitle}
                                </h3>
                                <p className="text-xs leading-relaxed text-muted-foreground line-clamp-2 sm:text-sm">
                                    {displayMood}
                                </p>
                            </div>
                            <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5 text-xs font-medium text-muted-foreground/80 sm:gap-x-4 sm:gap-y-2 md:gap-x-5">
                                <div className="flex items-center gap-1.5 sm:gap-2">
                                    <CalendarDays className="h-3 w-3 sm:h-3.5 sm:w-3.5" />
                                    <span className="text-[10px] sm:text-xs">{formatDate(playlist.created_at)}</span>
                                </div>
                                <div className="flex items-center gap-1.5 sm:gap-2">
                                    <Music className="h-3 w-3 sm:h-3.5 sm:w-3.5" />
                                    <span className="text-[10px] font-semibold text-foreground/70 sm:text-xs">{trackLabel}</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Right side - Status & Actions */}
                    <div className="flex shrink-0 flex-row items-end justify-between gap-3 border-t border-border/30 pt-3 sm:border-t-0 sm:pt-0 md:min-w-[200px] md:flex-col md:border-l md:border-t-0 md:pl-6 md:pt-0">

                        <div className="flex w-full flex-col gap-2">
                            <div className="flex items-center gap-2">
                                {playlist.session_id && isCompleted && (
                                    <Button asChild variant="default" size="sm" className="flex-1 h-9 gap-2 text-sm font-semibold shadow-md hover:shadow-lg transition-shadow">
                                        <Link
                                            href={`/playlist/${playlist.session_id}`}
                                            onClick={event => event.stopPropagation()}
                                        >
                                            <Play className="h-4 w-4" />
                                            <span>View</span>
                                        </Link>
                                    </Button>
                                )}

                                {playlist.session_id && !isCompleted && (
                                    <Button asChild variant="outline" size="sm" className="flex-1 h-9 gap-2 text-sm font-semibold border-2">
                                        <Link
                                            href={`/create/${playlist.session_id}`}
                                            onClick={event => event.stopPropagation()}
                                        >
                                            <Edit className="h-4 w-4" />
                                            <span>Continue</span>
                                        </Link>
                                    </Button>
                                )}
                            </div>

                            <div className="flex items-center justify-between gap-2">
                                {hasSpotifyUrl ? (
                                    <Button
                                        asChild
                                        variant="outline"
                                        size="sm"
                                        className="flex-1 h-9 gap-2 text-sm font-medium text-muted-foreground hover:bg-accent hover:text-foreground transition-all"
                                    >
                                        <a
                                            href={playlist.spotify_url ?? '#'}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            onClick={event => event.stopPropagation()}
                                            aria-label="Open in Spotify"
                                        >
                                            <ExternalLink className="h-4 w-4" />
                                            <span>Spotify</span>
                                        </a>
                                    </Button>
                                ) : (
                                    <div className="flex-1" />
                                )}

                                <Button
                                    type="button"
                                    variant="ghost"
                                    size="sm"
                                    onClick={handleDeleteClick}
                                    disabled={isDeleting}
                                    className="h-9 w-9 p-0 text-muted-foreground hover:bg-destructive/10 hover:text-destructive transition-all"
                                    aria-label="Delete playlist"
                                >
                                    <Trash2 className="h-4 w-4" />
                                </Button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </>
    );
}

