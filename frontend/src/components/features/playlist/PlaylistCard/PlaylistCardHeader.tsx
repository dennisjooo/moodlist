import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Music, Trash2 } from 'lucide-react';

interface PlaylistCardHeaderProps {
  trackCount: number;
  showDelete: boolean;
  onDelete: (e: React.MouseEvent) => void;
  isDeleting: boolean;
}

export function PlaylistCardHeader({
  trackCount,
  showDelete,
  onDelete,
  isDeleting,
}: PlaylistCardHeaderProps) {
  return (
    <div className="relative z-10 flex items-center justify-between">
      <div className="w-10 h-10 bg-white/20 backdrop-blur-sm rounded-full flex items-center justify-center">
        <Music className="w-5 h-5 text-white" />
      </div>
      <div className="flex items-center gap-2">
        {trackCount > 0 && (
          <Badge className="h-6 bg-white/20 backdrop-blur-sm text-white border-white/30 hover:bg-white/30">
            {trackCount} tracks
          </Badge>
        )}
        {showDelete && (
          <Button
            size="sm"
            variant="ghost"
            className="h-6 w-8 p-0 bg-white/10 backdrop-blur-sm hover:bg-red-500/80 text-white"
            onClick={onDelete}
            disabled={isDeleting}
          >
            <Trash2 className="w-3.5 h-3.5" />
          </Button>
        )}
      </div>
    </div>
  );
}

