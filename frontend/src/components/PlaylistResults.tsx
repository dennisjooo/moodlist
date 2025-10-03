'use client';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import { useWorkflow } from '@/lib/workflowContext';
import { Download, Edit, ExternalLink, Loader2, Music, Star } from 'lucide-react';
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

  const handleEditClick = () => {
    if (workflowState.sessionId) {
      router.push(`/create/${workflowState.sessionId}/edit`);
    }
  };

  return (
    <div className="space-y-6">
      {/* Draft/Saved Status Banner */}
      <Card className={cn(
        "border-2",
        hasSavedToSpotify ? "border-green-500 bg-green-50 dark:bg-green-950/20" : "border-yellow-500 bg-yellow-50 dark:bg-yellow-950/20"
      )}>
        <CardContent>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className={cn(
                "w-12 h-12 rounded-full flex items-center justify-center",
                hasSavedToSpotify ? "bg-green-500" : "bg-yellow-500"
              )}>
                <Music className="w-6 h-6 text-white" />
              </div>
              <div>
                <h3 className="font-semibold text-xl">{hasSavedToSpotify ? (workflowState.playlist?.name || 'Saved Playlist') : 'Your Draft Playlist'}</h3>
                <p className="text-sm text-muted-foreground mt-0.5">
                  {hasSavedToSpotify ? '✅ Saved to Spotify' : '📝 Based on'} "{workflowState.moodPrompt}" • {workflowState.recommendations.length} tracks
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              {hasSavedToSpotify ? (
                <>
                  <Button
                    variant="outline"
                    onClick={handleEditClick}
                    size="lg"
                    className="flex items-center gap-2"
                  >
                    <Edit className="w-4 h-4" />
                    Edit Playlist
                  </Button>
                  {workflowState.playlist?.spotify_url && (
                    <Button asChild size="lg">
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
                  )}
                </>
              ) : (
                <>
                  <Button
                    variant="outline"
                    onClick={handleEditClick}
                    size="lg"
                    className="flex items-center gap-2"
                  >
                    <Edit className="w-4 h-4" />
                    Edit Draft
                  </Button>
                  <Button
                    onClick={handleSaveToSpotify}
                    disabled={isSaving}
                    size="lg"
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
                </>
              )}
            </div>
          </div>

          {saveError && (
            <div className="mt-4 p-3 bg-red-100 dark:bg-red-950/50 border border-red-300 dark:border-red-800 rounded-md">
              <p className="text-sm text-red-800 dark:text-red-200">{saveError}</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Mood Analysis */}
      {workflowState.moodAnalysis && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Mood Analysis</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <p className="text-sm leading-relaxed text-muted-foreground">
                {workflowState.moodAnalysis.mood_interpretation}
              </p>

              <div className="flex flex-wrap gap-2">
                <Badge variant="secondary" className="capitalize">
                  {workflowState.moodAnalysis.primary_emotion}
                </Badge>
                <Badge variant="secondary" className="capitalize">
                  {workflowState.moodAnalysis.energy_level}
                </Badge>
                {workflowState.moodAnalysis.search_keywords && workflowState.moodAnalysis.search_keywords.slice(0, 6).map((keyword, idx) => (
                  <Badge key={idx} variant="outline" className="capitalize">
                    {keyword}
                  </Badge>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Track List */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Recommended Tracks</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {workflowState.recommendations.map((track, index) => (
              <div
                key={`track-${index}-${track.track_id}`}
                className="flex items-center gap-3 p-2.5 rounded-lg hover:bg-accent/50 transition-colors group"
              >
                <div className="flex-shrink-0 w-7 h-7 rounded-full bg-muted flex items-center justify-center text-xs font-medium text-muted-foreground">
                  {index + 1}
                </div>

                <div className="flex-1 min-w-0">
                  <h4 className="font-medium text-sm truncate">{track.track_name}</h4>
                  <p className="text-xs text-muted-foreground truncate">
                    {track.artists.join(', ')}
                  </p>
                </div>

                <div className="flex items-center gap-2 flex-shrink-0">
                  <div className="flex items-center gap-1">
                    <Star className="w-3 h-3 fill-yellow-400 text-yellow-400" />
                    <span className="text-xs text-muted-foreground">
                      {Math.round(track.confidence_score * 30 + 70)}%
                    </span>
                  </div>

                  {track.spotify_uri && (
                    <Button size="sm" variant="ghost" className="h-7 w-7 p-0 opacity-0 group-hover:opacity-100 transition-opacity" asChild>
                      <a
                        href={(() => {
                          const uri = track.spotify_uri;
                          if (uri.startsWith('http')) return uri;
                          if (uri.startsWith('spotify:track:')) {
                            return `https://open.spotify.com/track/${uri.split(':')[2]}`;
                          }
                          return `https://open.spotify.com/track/${uri}`;
                        })()}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        <ExternalLink className="w-3.5 h-3.5" />
                      </a>
                    </Button>
                  )}
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
            router.replace('/create');
          }}
          className="flex-1"
        >
          🔄 Create New Playlist
        </Button>
      </div>
    </div>
  );
}