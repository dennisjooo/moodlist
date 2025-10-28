import { MoodAnalysis } from '@/lib/api/playlist';

export interface PlaylistCardProps {
  mood: string;
  title: string;
  createdAt: string;
  trackCount: number;
  spotifyUrl: string;
  sessionId?: string;
  status?: string;
  playlistId?: number;
  moodAnalysis?: MoodAnalysis;
  onDelete?: (playlistId: number) => void;
  colorPrimary?: string;
  colorSecondary?: string;
  colorTertiary?: string;
}

export interface GradientStyle {
  className?: string;
  style?: React.CSSProperties;
}

