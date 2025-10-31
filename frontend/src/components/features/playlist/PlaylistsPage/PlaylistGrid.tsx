"use client";

import PlaylistCard from '@/components/features/playlist/PlaylistCard';
import { motion } from '@/components/ui/lazy-motion';
import { UserPlaylist } from '@/lib/api/playlist';
import { PlaylistListItem } from './PlaylistListItem';

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
