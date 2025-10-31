"use client";

import PlaylistCard from '@/components/features/playlist/PlaylistCard';
import { DeletePlaylistDialog } from '@/components/features/playlist/PlaylistCard/DeletePlaylistDialog';
import { usePlaylistCardDelete } from '@/components/features/playlist/PlaylistCard/usePlaylistCardDelete';
import { usePlaylistCardGradient } from '@/components/features/playlist/PlaylistCard/usePlaylistCardGradient';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { motion } from '@/components/ui/lazy-motion';
import { UserPlaylist } from '@/lib/api/playlist';
import { cn } from '@/lib/utils';
import { cleanText } from '@/lib/utils/text';
import { CalendarDays, Edit, ExternalLink, Music, Play, Trash2 } from 'lucide-react';
import Link from 'next/link';

interface PlaylistGridProps {
    playlists: UserPlaylist[];
    onDelete: (playlistId: number) => Promise<void>;
    formatDate: (dateString: string) => string;
    viewMode?: 'grid' | 'list';
}

export function PlaylistGrid({ playlists, onDelete, formatDate, viewMode = 'grid' }: PlaylistGridProps) {
    const containerClass = viewMode === 'list'
        ? 'space-y-4'
        : 'grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3';

    return (
        <motion.div
            initial="hidden"
            animate="visible"
            variants={{
                visible: {
                    transition: {
                        staggerChildren: 0.08,
                    },
                },
            }}
            className={containerClass}
        >
            {playlists.map(playlist => (
                <motion.div
                    key={playlist.id}
                    variants={{
                        hidden: { opacity: 0, y: 20 },
                        visible: { opacity: 1, y: 0 },
                    }}
                    transition={{ duration: 0.3 }}
                >
                    {viewMode === 'list' ? (
                        <PlaylistListItem
                            playlist={playlist}
                            onDelete={onDelete}
                            formatDate={formatDate}
                        />
                    ) : (
                        <PlaylistCard
                            mood={playlist.mood_prompt}
                            title={playlist.name || playlist.mood_prompt}
                            createdAt={formatDate(playlist.created_at)}
                            trackCount={playlist.track_count}
                            spotifyUrl={playlist.spotify_url || '#'}
                            sessionId={playlist.session_id}
                            status={playlist.status}
                            playlistId={playlist.id}
                            moodAnalysis={playlist.mood_analysis_data}
                            onDelete={onDelete}
                            colorPrimary={playlist.color_primary}
                            colorSecondary={playlist.color_secondary}
                            colorTertiary={playlist.color_tertiary}
                        />
                    )}
                </motion.div>
            ))}
        </motion.div>
    );
}

interface PlaylistListItemProps {
    playlist: UserPlaylist;
    onDelete: (playlistId: number) => Promise<void>;
    formatDate: (dateString: string) => string;
}

function PlaylistListItem({ playlist, onDelete, formatDate }: PlaylistListItemProps) {
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

            <div className="group relative overflow-hidden rounded-xl border border-border/60 bg-card/60 p-4 shadow-sm transition hover:border-primary/60 hover:shadow-lg">
                <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                    <div className="flex items-start gap-4">
                        <div className="h-14 w-14 shrink-0 overflow-hidden rounded-lg border border-border/50">
                            <div
                                className={cn('h-full w-full', gradient.className)}
                                style={gradient.style}
                            />
                        </div>
                        <div className="space-y-1">
                            <div className="flex flex-wrap items-center gap-2">
                                <h3 className="text-lg font-semibold leading-tight text-foreground">
                                    {displayTitle}
                                </h3>
                                <Badge variant="outline" className="capitalize text-xs">
                                    {playlist.status}
                                </Badge>
                            </div>
                            <p className="text-sm text-muted-foreground line-clamp-2">
                                {displayMood}
                            </p>
                        </div>
                    </div>

                    <div className="flex w-full flex-col gap-3 md:w-auto md:items-end">
                        <div className="flex flex-wrap items-center gap-4 text-sm text-muted-foreground md:justify-end">
                            <div className="flex items-center gap-2">
                                <CalendarDays className="h-4 w-4" />
                                <span>{formatDate(playlist.created_at)}</span>
                            </div>
                            <div className="flex items-center gap-2">
                                <Music className="h-4 w-4" />
                                <span>{trackLabel}</span>
                            </div>
                        </div>

                        <div className="flex flex-wrap items-center gap-2 md:justify-end">
                            {playlist.session_id && !isCompleted && (
                                <Button asChild variant="outline" size="sm" className="gap-1.5">
                                    <Link
                                        href={`/create/${playlist.session_id}`}
                                        onClick={event => event.stopPropagation()}
                                    >
                                        <Edit className="h-4 w-4" />
                                        Continue
                                    </Link>
                                </Button>
                            )}

                            {playlist.session_id && isCompleted && (
                                <Button asChild variant="outline" size="sm" className="gap-1.5">
                                    <Link
                                        href={`/playlist/${playlist.session_id}`}
                                        onClick={event => event.stopPropagation()}
                                    >
                                        <Play className="h-4 w-4" />
                                        View
                                    </Link>
                                </Button>
                            )}

                            {hasSpotifyUrl && (
                                <Button
                                    asChild
                                    variant="ghost"
                                    size="sm"
                                    className="text-muted-foreground hover:text-primary"
                                >
                                    <a
                                        href={playlist.spotify_url ?? '#'}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        onClick={event => event.stopPropagation()}
                                    >
                                        <ExternalLink className="h-4 w-4" />
                                        <span className="sr-only">Open in Spotify</span>
                                    </a>
                                </Button>
                            )}

                            <Button
                                type="button"
                                variant="ghost"
                                size="sm"
                                onClick={handleDeleteClick}
                                disabled={isDeleting}
                                className="text-destructive hover:text-destructive"
                            >
                                <Trash2 className="h-4 w-4" />
                                <span className="sr-only">Delete playlist</span>
                            </Button>
                        </div>
                    </div>
                </div>
            </div>
        </>
    );
}
