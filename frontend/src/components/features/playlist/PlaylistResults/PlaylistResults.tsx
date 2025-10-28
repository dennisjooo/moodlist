'use client';

import { Button } from '@/components/ui/button';
import { playlistAPI } from '@/lib/playlistApi';
import { useWorkflow } from '@/lib/contexts/WorkflowContext';
import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { useToast } from '@/lib/hooks/useToast';
import { logger } from '@/lib/utils/logger';
import PlaylistStatusBanner from './PlaylistStatusBanner';
import MoodAnalysisCard from './MoodAnalysisCard';
import TrackListView from './TrackListView';
import DeletePlaylistDialog from './DeletePlaylistDialog';

export default function PlaylistResults() {
  const router = useRouter();
  const { workflowState, saveToSpotify, syncFromSpotify, resetWorkflow } = useWorkflow();
  const [isSaving, setIsSaving] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const { success, error: showError } = useToast();

  const handleSaveToSpotify = async () => {
    setIsSaving(true);

    try {
      await saveToSpotify();
      success('Playlist saved to Spotify!');
    } catch (error) {
      showError(error instanceof Error ? error.message : 'Failed to save playlist');
    } finally {
      setIsSaving(false);
    }
  };

  const handleSyncFromSpotify = async () => {
    setIsSyncing(true);

    try {
      const result = await syncFromSpotify();
      if (result.synced) {
        const changes = result.changes;
        if (changes && (changes.tracks_added > 0 || changes.tracks_removed > 0)) {
          success('Playlist synced!', {
            description: `${changes.tracks_added > 0 ? `Added ${changes.tracks_added} track(s). ` : ''}${changes.tracks_removed > 0 ? `Removed ${changes.tracks_removed} track(s).` : ''}`.trim()
          });
        } else {
          success('Playlist is up to date!');
        }
      } else {
        showError(result.message || 'Could not sync playlist');
      }
    } catch (error) {
      showError(error instanceof Error ? error.message : 'Failed to sync from Spotify');
    } finally {
      setIsSyncing(false);
    }
  };

  const handleDelete = async () => {
    if (!workflowState.sessionId) return;

    setIsDeleting(true);
    try {
      // Get the playlist database ID using the session ID
      const playlistData = await playlistAPI.getPlaylistBySession(workflowState.sessionId);
      // Delete the playlist
      await playlistAPI.deletePlaylist(playlistData.id);
      success('Playlist deleted');
      // Navigate back to playlists page
      router.push('/playlists');
    } catch (error) {
      logger.error('Failed to delete playlist', error, { component: 'PlaylistResults', sessionId: workflowState.sessionId });
      showError('Failed to delete playlist. Please try again.');
      setIsDeleting(false);
      setShowDeleteDialog(false);
    }
  };

  if (!workflowState.recommendations || workflowState.recommendations.length === 0) {
    return null;
  }

  const hasSavedToSpotify = workflowState.playlist?.id;

  const handleEditClick = () => {
    if (workflowState.sessionId) {
      router.push(`/playlist/${workflowState.sessionId}/edit`);
    }
  };

  const colorScheme = workflowState.moodAnalysis?.color_scheme;

  return (
    <div className="space-y-6">
      {/* Status Banner */}
      <PlaylistStatusBanner
        hasSavedToSpotify={!!hasSavedToSpotify}
        playlistName={workflowState.playlist?.name}
        moodPrompt={workflowState.moodPrompt}
        trackCount={workflowState.recommendations.length}
        spotifyUrl={workflowState.playlist?.spotify_url}
        isSaving={isSaving}
        isSyncing={isSyncing}
        isDeleting={isDeleting}
        onSaveToSpotify={handleSaveToSpotify}
        onSyncFromSpotify={handleSyncFromSpotify}
        onEdit={handleEditClick}
        onDelete={() => setShowDeleteDialog(true)}
        colorScheme={colorScheme}
      />

      {/* Delete Confirmation Dialog */}
      <DeletePlaylistDialog
        open={showDeleteDialog}
        onOpenChange={setShowDeleteDialog}
        playlistName={workflowState.playlist?.name || workflowState.moodPrompt}
        isDeleting={isDeleting}
        onConfirm={handleDelete}
      />

      {/* Mood Analysis */}
      {workflowState.moodAnalysis && (
        <MoodAnalysisCard 
          moodAnalysis={workflowState.moodAnalysis} 
          metadata={workflowState.metadata}
        />
      )}

      {/* Track List */}
      <TrackListView tracks={workflowState.recommendations} />

      {/* Actions */}
      <div className="flex gap-3">
        <Button
          variant="outline"
          onClick={() => {
            logger.debug('Create New Playlist button clicked', { component: 'PlaylistResults' });
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

