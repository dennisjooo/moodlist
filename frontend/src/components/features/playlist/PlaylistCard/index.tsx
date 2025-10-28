import { cleanText } from '@/lib/utils/text';
import { PlaylistCardProps } from './types';
import { usePlaylistCardGradient } from './usePlaylistCardGradient';
import { usePlaylistCardDelete } from './usePlaylistCardDelete';
import { DeletePlaylistDialog } from './DeletePlaylistDialog';
import { PlaylistCardHeader } from './PlaylistCardHeader';
import { PlaylistCardContent } from './PlaylistCardContent';
import { PlaylistCardActions } from './PlaylistCardActions';

export default function PlaylistCard({
  mood,
  title,
  createdAt,
  trackCount,
  spotifyUrl,
  sessionId,
  status,
  playlistId,
  moodAnalysis,
  onDelete,
  colorPrimary,
  colorSecondary,
  colorTertiary,
}: PlaylistCardProps) {
  const isCompleted = status === 'completed';

  // Hooks
  const gradient = usePlaylistCardGradient({
    mood,
    colorPrimary,
    colorSecondary,
    colorTertiary,
  });

  const {
    isDeleting,
    showDeleteDialog,
    setShowDeleteDialog,
    handleDeleteClick,
    handleConfirmDelete,
  } = usePlaylistCardDelete({ playlistId, onDelete });

  // Display text
  const displayMood = cleanText(moodAnalysis?.mood_interpretation || mood);
  const displayTitle = cleanText(title);

  return (
    <>
      <DeletePlaylistDialog
        open={showDeleteDialog}
        onOpenChange={setShowDeleteDialog}
        onConfirm={handleConfirmDelete}
        playlistTitle={displayTitle}
        isDeleting={isDeleting}
      />

      <div
        className="group transition-all duration-300 hover:scale-105 hover:shadow-xl rounded-lg overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div
          className={`${gradient.className || ''} h-[320px] flex flex-col justify-between p-6 relative`}
          style={gradient.style}
        >
          <div className="absolute inset-0 bg-black/10 group-hover:bg-black/5 transition-colors" />

          <PlaylistCardHeader
            trackCount={trackCount}
            showDelete={!!(playlistId && onDelete)}
            onDelete={handleDeleteClick}
            isDeleting={isDeleting}
          />

          <PlaylistCardContent
            title={displayTitle}
            mood={displayMood}
            createdAt={createdAt}
            moodAnalysis={moodAnalysis}
          />

          <PlaylistCardActions
            sessionId={sessionId}
            isCompleted={isCompleted}
            spotifyUrl={spotifyUrl}
          />
        </div>
      </div>
    </>
  );
}

