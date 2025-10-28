import { Badge } from '@/components/ui/badge';
import { MoodAnalysis } from '@/lib/api/playlist';
import { Calendar } from 'lucide-react';

interface PlaylistCardContentProps {
  title: string;
  mood: string;
  createdAt: string;
  moodAnalysis?: MoodAnalysis;
}

export function PlaylistCardContent({
  title,
  mood,
  createdAt,
  moodAnalysis,
}: PlaylistCardContentProps) {
  return (
    <div className="relative z-10 flex flex-col h-full">
      {/* Title section */}
      <div className="my-3">
        <h3 className="font-bold text-white text-lg leading-tight mb-2 drop-shadow-sm line-clamp-2">
          {title}
        </h3>
      </div>

      {/* Description section */}
      <div className="mb-3 min-h-[60px]">
        <p className="text-sm text-white/90 drop-shadow-sm line-clamp-2 mb-2">{mood}</p>
        <div className="flex flex-wrap gap-1.5 min-h-[24px]">
          {moodAnalysis?.primary_emotion && (
            <>
              <Badge
                variant="secondary"
                className="text-xs bg-white/25 backdrop-blur-sm text-white border-white/30 hover:bg-white/35 inline-block truncate max-w-[120px]"
              >
                <span className="truncate block">{moodAnalysis.primary_emotion}</span>
              </Badge>
              {moodAnalysis.energy_level && (
                <Badge
                  variant="secondary"
                  className="text-xs bg-white/25 backdrop-blur-sm text-white border-white/30 hover:bg-white/35 inline-block truncate max-w-[120px]"
                >
                  <span className="truncate block">{moodAnalysis.energy_level}</span>
                </Badge>
              )}
            </>
          )}
        </div>
      </div>

      {/* Date section */}
      <div className="mb-4">
        <div className="flex items-center text-sm text-white/80">
          <Calendar className="w-4 h-4 mr-2" />
          Created {new Date(createdAt).toLocaleDateString()}
        </div>
      </div>
    </div>
  );
}

