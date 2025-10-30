import type { LucideIcon } from 'lucide-react';
import { Music } from 'lucide-react';

interface MoodCardProps {
  name: string;
  description: string;
  icon?: LucideIcon;
  genre: string;
  gradient: string;
  onClick?: () => void;
  className?: string;
}

export default function MoodCard({ name, description, icon, genre, gradient, onClick, className }: MoodCardProps) {
  const IconComponent = icon || Music;

  return (
    <div
      className={`${gradient} rounded-2xl cursor-pointer transition-all duration-500 hover:scale-[1.02] hover:shadow-2xl h-72 flex flex-col relative overflow-hidden group ${className || ''}`}
      onClick={onClick}
    >
      {/* Gradient Overlay */}
      <div className="absolute inset-0 bg-gradient-to-b from-black/20 via-black/10 to-black/60 group-hover:from-black/10 group-hover:to-black/50 transition-all duration-500" />

      {/* Subtle Pattern Overlay */}
      <div className="absolute inset-0 opacity-10 bg-[radial-gradient(circle_at_50%_120%,rgba(255,255,255,0.8),transparent_50%)]" />

      {/* Content Container */}
      <div className="relative z-10 flex flex-col h-full p-6 justify-between">
        {/* Top Section - Icon */}
        <div className="flex justify-start">
          <div className="w-12 h-12 bg-white/25 backdrop-blur-md rounded-xl flex items-center justify-center group-hover:scale-110 group-hover:bg-white/30 transition-all duration-300 shadow-lg">
            <IconComponent className="w-6 h-6 text-white drop-shadow-md" />
          </div>
        </div>

        {/* Bottom Section - Text & Tags */}
        <div className="space-y-3">
          <div className="space-y-2">
            <h3 className="font-bold text-white text-xl leading-tight drop-shadow-lg">
              {name}
            </h3>
            <p className="text-sm text-white/90 drop-shadow-md leading-relaxed line-clamp-2">
              {description}
            </p>
          </div>

          {/* Tags */}
          <div className="flex flex-wrap gap-2">
            <span className="px-3 py-1 bg-white/20 backdrop-blur-md rounded-full text-xs text-white border border-white/30 shadow-sm">
              {genre}
            </span>
          </div>
        </div>
      </div>

      {/* Bottom Shine Effect */}
      <div className="absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-white/40 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
    </div>
  );
}

