'use client';

import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { Pause, Play, Volume2 } from 'lucide-react';
import { useCallback, useEffect, useRef, useState, type MouseEvent } from 'react';

interface AudioPreviewPlayerProps {
    previewUrl: string;
    trackName: string;
    compact?: boolean;
}

export function AudioPreviewPlayer({ previewUrl, trackName, compact = false }: AudioPreviewPlayerProps) {
    const [isPlaying, setIsPlaying] = useState(false);
    const [currentTime, setCurrentTime] = useState(0);
    const [duration, setDuration] = useState(30); // Spotify preview is 30 seconds
    const audioRef = useRef<HTMLAudioElement | null>(null);

    useEffect(() => {
        if (!previewUrl) return;

        // Create audio element
        const audio = new Audio(previewUrl);
        audioRef.current = audio;

        // Set event listeners
        audio.addEventListener('loadedmetadata', () => {
            setDuration(audio.duration);
        });

        audio.addEventListener('timeupdate', () => {
            setCurrentTime(audio.currentTime);
        });

        audio.addEventListener('ended', () => {
            setIsPlaying(false);
            setCurrentTime(0);
        });

        audio.addEventListener('error', () => {
            console.error('Error loading audio preview');
            setIsPlaying(false);
        });

        return () => {
            audio.pause();
            audio.src = '';
            audioRef.current = null;
        };
    }, [previewUrl]);

    const handlePlayPause = useCallback((e: MouseEvent<HTMLButtonElement>) => {
        e.preventDefault();
        e.stopPropagation();

        if (!audioRef.current) return;

        if (isPlaying) {
            audioRef.current.pause();
            setIsPlaying(false);
        } else {
            audioRef.current.play().catch(err => {
                console.error('Error playing audio:', err);
                setIsPlaying(false);
            });
            setIsPlaying(true);
        }
    }, [isPlaying]);

    const progress = (currentTime / duration) * 100;

    if (compact) {
        return (
            <Button
                size="sm"
                variant="ghost"
                className="h-8 w-8 p-0"
                onClick={handlePlayPause}
                aria-label={isPlaying ? `Pause preview of ${trackName}` : `Play preview of ${trackName}`}
            >
                {isPlaying ? (
                    <Pause className="w-4 h-4" />
                ) : (
                    <Play className="w-4 h-4" />
                )}
            </Button>
        );
    }

    return (
        <div className="flex items-center gap-2 w-full">
            <Button
                size="sm"
                variant="ghost"
                className="h-8 w-8 p-0 flex-shrink-0"
                onClick={handlePlayPause}
                aria-label={isPlaying ? `Pause preview of ${trackName}` : `Play preview of ${trackName}`}
            >
                {isPlaying ? (
                    <Pause className="w-4 h-4" />
                ) : (
                    <Play className="w-4 h-4" />
                )}
            </Button>
            
            <div className="flex-1 h-1.5 bg-muted rounded-full overflow-hidden">
                <div 
                    className={cn(
                        "h-full bg-primary transition-all duration-150",
                        isPlaying && "animate-pulse"
                    )}
                    style={{ width: `${progress}%` }}
                />
            </div>

            <div className="flex items-center gap-1 text-xs text-muted-foreground flex-shrink-0">
                <Volume2 className="w-3 h-3" />
                <span>{Math.floor(currentTime)}s</span>
            </div>
        </div>
    );
}
