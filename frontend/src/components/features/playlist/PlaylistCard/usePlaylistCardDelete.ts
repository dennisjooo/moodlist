import { useState } from 'react';
import { logger } from '@/lib/utils/logger';

interface UsePlaylistCardDeleteProps {
  playlistId?: number;
  onDelete?: (playlistId: number) => void;
}

export function usePlaylistCardDelete({ playlistId, onDelete }: UsePlaylistCardDeleteProps) {
  const [isDeleting, setIsDeleting] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);

  const handleDeleteClick = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setShowDeleteDialog(true);
  };

  const handleConfirmDelete = async () => {
    if (!playlistId || !onDelete) return;

    setIsDeleting(true);
    try {
      await onDelete(playlistId);
      setShowDeleteDialog(false);
    } catch (error) {
      logger.error('Failed to delete playlist card item', error, {
        component: 'PlaylistCard',
        playlistId,
      });
      setIsDeleting(false);
    }
  };

  const handleCancelDelete = () => {
    setShowDeleteDialog(false);
  };

  return {
    isDeleting,
    showDeleteDialog,
    setShowDeleteDialog,
    handleDeleteClick,
    handleConfirmDelete,
    handleCancelDelete,
  };
}

