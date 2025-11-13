'use client';

import { Button } from '@/components/ui/button';
import { playlistAPI } from '@/lib/playlistApi';
import { useWorkflow } from '@/lib/contexts/WorkflowContext';
import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { useToast } from '@/lib/hooks';
import { logger } from '@/lib/utils/logger';
import { motion } from '@/components/ui/lazy-motion';
import { FADE_IN_VARIANTS, ACTIONS_FADE_IN_UP_VARIANTS } from '@/lib/constants/animations';
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
        const coverRetry = result.cover_upload_retry;

        // Build description with track changes and cover retry info
        let description = '';
        if (changes && (changes.tracks_added > 0 || changes.tracks_removed > 0)) {
          description = `${changes.tracks_added > 0 ? `Added ${changes.tracks_added} track(s). ` : ''}${changes.tracks_removed > 0 ? `Removed ${changes.tracks_removed} track(s).` : ''}`.trim();
        }

        // Add cover retry info if applicable
        if (coverRetry?.success) {
          description += (description ? ' ' : '') + 'Cover image uploaded successfully!';
        } else if (coverRetry?.attempted && !coverRetry?.success) {
          description += (description ? ' ' : '') + 'Note: Cover image upload is still pending.';
        }

        if (description || coverRetry?.success) {
          success('Playlist synced!', description ? { description } : undefined);
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
    <motion.div
      className="space-y-6"
      variants={FADE_IN_VARIANTS}
      initial="hidden"
      animate="visible"
    >
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
          totalLLMCost={workflowState.totalLLMCost}
          totalPromptTokens={workflowState.totalPromptTokens}
          totalCompletionTokens={workflowState.totalCompletionTokens}
          totalTokens={workflowState.totalTokens}
        />
      )}

      {/* Track List */}
      <TrackListView tracks={workflowState.recommendations} />

      {/* Actions */}
      <motion.div
        className="flex gap-3"
        variants={ACTIONS_FADE_IN_UP_VARIANTS}
        initial="hidden"
        animate="visible"
      >
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
      </motion.div>
    </motion.div>
  );
}

