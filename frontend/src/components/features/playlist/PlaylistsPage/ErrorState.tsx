import { Button } from '@/components/ui/button';
import { motion } from '@/components/ui/lazy-motion';
import { Music } from 'lucide-react';

interface ErrorStateProps {
    error: string;
    onRetry: () => void;
}

export function ErrorState({ error, onRetry }: ErrorStateProps) {
    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
            className="text-center py-12"
        >
            <Music className="w-16 h-16 text-destructive mx-auto mb-4" />
            <h3 className="text-xl font-semibold mb-2">Failed to load playlists</h3>
            <p className="text-muted-foreground mb-6">{error}</p>
            <Button onClick={onRetry}>Try Again</Button>
        </motion.div>
    );
}

