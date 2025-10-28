import { Button } from '@/components/ui/button';
import { Edit, ExternalLink, Play } from 'lucide-react';
import Link from 'next/link';

interface PlaylistCardActionsProps {
    sessionId?: string;
    isCompleted: boolean;
    spotifyUrl: string;
}

export function PlaylistCardActions({
    sessionId,
    isCompleted,
    spotifyUrl,
}: PlaylistCardActionsProps) {
    const hasValidSpotifyUrl = spotifyUrl && spotifyUrl !== '#';

    return (
        <div className="mt-auto flex gap-2">
            {sessionId && !isCompleted && (
                <Link href={`/create/${sessionId}`} className="flex-1" onClick={(e) => e.stopPropagation()}>
                    <Button
                        size="sm"
                        className="w-full bg-white/20 backdrop-blur-sm hover:bg-white/30 text-white border-white/30"
                        variant="outline"
                    >
                        <Edit className="w-4 h-4 mr-2" />
                        Continue
                    </Button>
                </Link>
            )}
            {sessionId && isCompleted && (
                <Link
                    href={`/playlist/${sessionId}`}
                    className="flex-1"
                    onClick={(e) => e.stopPropagation()}
                >
                    <Button
                        size="sm"
                        className="w-full bg-white/20 backdrop-blur-sm hover:bg-white/30 text-white border-white/30"
                        variant="outline"
                    >
                        <Play className="w-4 h-4 mr-2" />
                        View
                    </Button>
                </Link>
            )}
            {hasValidSpotifyUrl && (
                <a
                    href={spotifyUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={(e) => e.stopPropagation()}
                >
                    <Button
                        size="sm"
                        className="bg-white/20 backdrop-blur-sm hover:bg-white/30 text-white border-white/30"
                        variant="outline"
                    >
                        <ExternalLink className="w-4 h-4" />
                    </Button>
                </a>
            )}
        </div>
    );
}

