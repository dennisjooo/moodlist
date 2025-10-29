import { Badge } from '@/components/ui/badge';
import { Music } from 'lucide-react';

export function PlaylistsPageHeader() {
    return (
        <div className="text-center mb-12">
            <Badge variant="outline" className="px-4 py-1 flex items-center gap-2 w-fit mx-auto mb-6">
                <Music className="w-4 h-4" />
                Your Music History
            </Badge>

            <h1 className="text-4xl font-bold tracking-tight text-foreground sm:text-5xl mb-4">
                My Playlists
            </h1>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
                All your mood-based playlists in one place. Relive your musical moments.
            </p>
        </div>
    );
}

