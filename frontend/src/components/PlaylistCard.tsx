import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { generateMoodGradient } from '@/lib/moodColors';
import { Calendar, ExternalLink, Music, Play } from 'lucide-react';

interface PlaylistCardProps {
  mood: string;
  title: string;
  createdAt: string;
  trackCount: number;
  spotifyUrl: string;
}

export default function PlaylistCard({ mood, title, createdAt, trackCount, spotifyUrl }: PlaylistCardProps) {
  const autoGradient = generateMoodGradient(mood);

  return (
    <div className="group cursor-pointer transition-all duration-300 hover:scale-105 hover:shadow-xl rounded-lg overflow-hidden">
      {/* Full Gradient Background */}
      <div className={`${autoGradient} h-64 flex flex-col justify-between p-6 relative`}>
        <div className="absolute inset-0 bg-black/10 group-hover:bg-black/5 transition-colors" />
        
        {/* Header */}
        <div className="relative z-10 flex items-center justify-between">
          <div className="w-10 h-10 bg-white/20 backdrop-blur-sm rounded-full flex items-center justify-center">
            <Music className="w-5 h-5 text-white" />
          </div>
          <Badge className="bg-white/20 backdrop-blur-sm text-white border-white/30 hover:bg-white/30">
            {trackCount} tracks
          </Badge>
        </div>
        
        {/* Content */}
        <div className="relative z-10 space-y-3">
          <div>
            <h3 className="font-bold text-white text-lg mb-1 drop-shadow-sm">{title}</h3>
            <p className="text-sm text-white/90 drop-shadow-sm">"{mood}"</p>
          </div>
          
          <div className="flex items-center text-sm text-white/80 mb-4">
            <Calendar className="w-4 h-4 mr-2" />
            Created {new Date(createdAt).toLocaleDateString()}
          </div>
          
          <div className="flex gap-2">
            <Button 
              size="sm" 
              className="flex-1 bg-white/20 backdrop-blur-sm hover:bg-white/30 text-white border-white/30"
              variant="outline"
            >
              <Play className="w-4 h-4 mr-2" />
              Play
            </Button>
            <Button 
              size="sm" 
              className="bg-white/20 backdrop-blur-sm hover:bg-white/30 text-white border-white/30"
              variant="outline"
            >
              <ExternalLink className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}