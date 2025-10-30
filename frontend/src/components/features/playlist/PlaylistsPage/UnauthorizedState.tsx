import { SpotifyLoginButton } from '@/components/features/auth/SpotifyLoginButton';
import { motion } from '@/components/ui/lazy-motion';
import { Music } from 'lucide-react';

export function UnauthorizedState() {
    return (
        <div className="flex items-center justify-center min-h-[calc(100vh-200px)]">
            <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.4 }}
                className="text-center max-w-lg mx-auto"
            >
                <Music className="w-16 h-16 text-muted-foreground mx-auto mb-4" />
                <h3 className="text-2xl font-semibold mb-3">Login to View Your Playlists</h3>
                <p className="text-muted-foreground mb-8">
                    Connect your Spotify account to access your personalized mood-based playlists.
                    All your musical moments, saved in one place.
                </p>
                <div className="flex justify-center mb-6">
                    <SpotifyLoginButton />
                </div>
                <p className="text-sm text-muted-foreground">
                    New here? Create your first playlist after logging in!
                </p>
            </motion.div>
        </div>
    );
}

