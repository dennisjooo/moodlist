import PlaylistCard from '@/components/features/playlist/PlaylistCard';
import { motion } from '@/components/ui/lazy-motion';
import { UserPlaylist } from '@/lib/api/playlist';

interface PlaylistGridProps {
    playlists: UserPlaylist[];
    onDelete: (playlistId: number) => Promise<void>;
    formatDate: (dateString: string) => string;
}

export function PlaylistGrid({ playlists, onDelete, formatDate }: PlaylistGridProps) {
    return (
        <motion.div
            initial="hidden"
            animate="visible"
            variants={{
                visible: {
                    transition: {
                        staggerChildren: 0.1
                    }
                }
            }}
            className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
        >
            {playlists.map((playlist) => (
                <motion.div
                    key={playlist.id}
                    variants={{
                        hidden: { opacity: 0, y: 20 },
                        visible: { opacity: 1, y: 0 }
                    }}
                    transition={{ duration: 0.4 }}
                >
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
                </motion.div>
            ))}
        </motion.div>
    );
}

