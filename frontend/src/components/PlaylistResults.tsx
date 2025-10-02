'use client';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import { useWorkflow } from '@/lib/workflowContext';
import { Download, ExternalLink, Loader2, Music, Star } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

interface PlaylistResultsProps {
  onEdit?: () => void;
  onNewPlaylist?: () => void;
}

export default function PlaylistResults({ onEdit, onNewPlaylist }: PlaylistResultsProps = {}) {
  const router = useRouter();
  const { workflowState, saveToSpotify, resetWorkflow } = useWorkflow();
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const handleSaveToSpotify = async () => {
    setIsSaving(true);
    setSaveError(null);

    try {
      await saveToSpotify();
    } catch (error) {
      setSaveError(error instanceof Error ? error.message : 'Failed to save playlist');
    } finally {
      setIsSaving(false);
    }
  };

  if (!workflowState.recommendations || workflowState.recommendations.length === 0) {
    return null;
  }

  const hasSavedToSpotify = workflowState.playlist?.id;

  return (
    <div className="space-y-6">
      {/* Draft/Saved Status Banner */}
      <Card className={cn(
        "border-2",
        hasSavedToSpotify ? "border-green-500 bg-green-50 dark:bg-green-950/20" : "border-yellow-500 bg-yellow-50 dark:bg-yellow-950/20"
      )}>
        <CardContent>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {hasSavedToSpotify ? (
                <>
                  <div className="w-10 h-10 rounded-full bg-green-500 flex items-center justify-center">
                    <Music className="w-5 h-5 text-white" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-lg">{workflowState.playlist?.name || 'Saved Playlist'}</h3>
                    <p className="text-sm text-muted-foreground">
                      ✅ Saved to Spotify • {workflowState.recommendations.length} tracks
                    </p>
                  </div>
                </>
              ) : (
                <>
                  <div className="w-10 h-10 rounded-full bg-yellow-500 flex items-center justify-center">
                    <Music className="w-5 h-5 text-white" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-lg">Your Draft Playlist</h3>
                    <p className="text-sm text-muted-foreground">
                      📝 {workflowState.recommendations.length} tracks • Based on "{workflowState.moodPrompt}"
                    </p>
                  </div>
                </>
              )}
            </div>

            {hasSavedToSpotify && workflowState.playlist?.spotify_url ? (
              <Button asChild>
                <a
                  href={workflowState.playlist.spotify_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2"
                >
                  <ExternalLink className="w-4 h-4" />
                  Open in Spotify
                </a>
              </Button>
            ) : (
              <Button
                onClick={handleSaveToSpotify}
                disabled={isSaving}
                className="flex items-center gap-2"
              >
                {isSaving ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Saving...
                  </>
                ) : (
                  <>
                    <Download className="w-4 h-4" />
                    Save to Spotify
                  </>
                )}
              </Button>
            )}
          </div>

          {saveError && (
            <div className="mt-3 p-3 bg-red-100 dark:bg-red-950/50 border border-red-300 dark:border-red-800 rounded-md">
              <p className="text-sm text-red-800 dark:text-red-200">{saveError}</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Mood Analysis */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Mood Analysis</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <h4 className="font-medium mb-2">Primary Emotion</h4>
              <Badge variant="outline">Energetic</Badge>
            </div>
            <div>
              <h4 className="font-medium mb-2">Energy Level</h4>
              <Badge variant="outline">High</Badge>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Track List */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Recommended Tracks</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {workflowState.recommendations.map((track, index) => (
              <div
                key={`track-${index}-${track.track_id}`}
                className={cn(
                  "flex items-center gap-4 p-3 rounded-lg border bg-card hover:bg-accent/50 transition-colors",
                  index === 0 && "bg-primary/5 border-primary/20"
                )}
              >
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center text-sm font-medium">
                  {index + 1}
                </div>

                <div className="flex-1 min-w-0">
                  <h4 className="font-medium truncate">{track.track_name}</h4>
                  <p className="text-sm text-muted-foreground truncate">
                    {track.artists.join(', ')}
                  </p>
                </div>

                <div className="flex items-center gap-3 flex-shrink-0">
                  <div className="text-right text-sm">
                    <div className="flex items-center gap-1">
                      <Star className="w-3 h-3 fill-yellow-400 text-yellow-400" />
                      <span className="text-muted-foreground">
                        {Math.round(track.confidence_score * 100)}%
                      </span>
                    </div>
                    <div className="text-xs text-muted-foreground capitalize">
                      {track.source}
                    </div>
                  </div>

                  {track.spotify_uri && (
                    <Button size="sm" variant="outline" asChild>
                      <a
                        href={(() => {
                          const uri = track.spotify_uri;
                          // If already a URL, use it
                          if (uri.startsWith('http')) return uri;
                          // If spotify:track:ID format, convert to URL
                          if (uri.startsWith('spotify:track:')) {
                            return `https://open.spotify.com/track/${uri.split(':')[2]}`;
                          }
                          // If just an ID, convert to URL
                          return `https://open.spotify.com/track/${uri}`;
                        })()}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    </Button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Reasoning */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">AI Reasoning</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {workflowState.recommendations.slice(0, 3).map((track, index) => (
              <div key={`reasoning-${index}-${track.track_id}`} className="p-3 rounded-lg bg-muted/50">
                <div className="flex items-start gap-2">
                  <Music className="w-4 h-4 mt-0.5 text-muted-foreground flex-shrink-0" />
                  <div>
                    <span className="font-medium">{track.track_name}</span>
                    <p className="text-sm text-muted-foreground mt-1">
                      {track.reasoning}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Actions */}
      <div className="flex gap-3">
        <Button
          variant="outline"
          onClick={() => {
            console.log('Create New Playlist button clicked');
            resetWorkflow();
            router.push('/create');
          }}
          className="flex-1"
        >
          🔄 Create New Playlist
        </Button>
      </div>
    </div>
  );
}