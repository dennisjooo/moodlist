import { Music, Coffee, Zap, BookOpen, Car, Heart, Cloud, PartyPopper, Sun, Headphones, Gamepad2, Sparkles } from 'lucide-react';
import { generateMoodGradient, getMoodGenre } from '@/lib/moodColors';

interface MoodCardProps {
  mood: string;
  genre?: string;
  gradient?: string;
  onClick?: () => void;
  className?: string;
}

// Function to get appropriate icon based on mood
function getMoodIcon(mood: string) {
  const moodLower = mood.toLowerCase();

  if (moodLower.includes('coffee') || moodLower.includes('morning')) return Coffee;
  if (moodLower.includes('workout') || moodLower.includes('energy')) return Zap;
  if (moodLower.includes('study') || moodLower.includes('focus')) return BookOpen;
  if (moodLower.includes('road') || moodLower.includes('trip') || moodLower.includes('travel')) return Car;
  if (moodLower.includes('romantic') || moodLower.includes('love')) return Heart;
  if (moodLower.includes('rainy') || moodLower.includes('chill') || moodLower.includes('calm')) return Cloud;
  if (moodLower.includes('party') || moodLower.includes('dance')) return PartyPopper;
  if (moodLower.includes('sunny') || moodLower.includes('bright') || moodLower.includes('happy')) return Sun;
  if (moodLower.includes('electronic') || moodLower.includes('techno')) return Headphones;
  if (moodLower.includes('game') || moodLower.includes('fun')) return Gamepad2;
  if (moodLower.includes('magic') || moodLower.includes('dream')) return Sparkles;

  // Default to Music icon
  return Music;
}

export default function MoodCard({ mood, genre, gradient, onClick, className }: MoodCardProps) {
  // Auto-generate gradient and genre if not provided
  const autoGradient = gradient || generateMoodGradient(mood);
  const autoGenre = genre || getMoodGenre(mood);
  const IconComponent = getMoodIcon(mood);
  return (
    <div
      className={`${autoGradient} rounded-lg cursor-pointer transition-all duration-300 hover:scale-105 hover:shadow-xl h-40 flex-col items-center justify-center relative p-6 text-center group ${className || ''}`}
      onClick={onClick}
    >
      <div className="absolute inset-0 bg-black/10 group-hover:bg-black/5 transition-colors rounded-lg" />

      {/* Mood Icon */}
      <div className="relative z-10 w-12 h-12 bg-white/20 backdrop-blur-sm rounded-full flex items-center justify-center group-hover:scale-110 transition-transform mb-4">
        <IconComponent className="w-6 h-6 text-white" />
      </div>

      {/* Text Content */}
      <div className="relative z-10">
        <h3 className="font-semibold text-white text-sm mb-1 drop-shadow-sm">{mood}</h3>
        <p className="text-xs text-white/90 drop-shadow-sm">{autoGenre}</p>
      </div>
    </div>
  );
}