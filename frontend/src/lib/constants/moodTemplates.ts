/**
 * Curated mood templates for quick playlist creation
 * These templates help onboard new users and provide inspiration
 */

import type { LucideIcon } from 'lucide-react';
import {
  Coffee,
  Zap,
  CloudRain,
  PartyPopper,
  BookOpen,
  Car,
  Sparkles,
  Heart,
  Moon,
  Guitar,
  Headphones,
  Waves,
  Music,
  Sun,
  Cloud,
  Gamepad2,
  Palmtree,
  Plane,
  Mountain,
  CircleDot,
} from 'lucide-react';

export interface MoodTemplate {
  name: string;
  prompt: string;
  icon: LucideIcon;
  genre: string;
  gradient: string;
  category: 'energy' | 'focus' | 'relax' | 'social' | 'activity';
}

export const MOOD_TEMPLATES: MoodTemplate[] = [
  {
    name: 'Morning Coffee',
    prompt: 'Smooth jazz, acoustic, and mellow morning tunes with warm, laid-back vibes perfect for sipping coffee and easing into the day',
    icon: Coffee,
    genre: 'Jazz',
    gradient: 'bg-gradient-to-br from-amber-400 via-orange-500 to-red-500',
    category: 'relax',
  },
  {
    name: 'Workout Energy',
    prompt: 'High-energy EDM, hip-hop, and rock with driving beats and motivational lyrics to power through an intense workout',
    icon: Zap,
    genre: 'EDM',
    gradient: 'bg-gradient-to-br from-red-400 via-pink-500 to-rose-600',
    category: 'energy',
  },
  {
    name: 'Rainy Day',
    prompt: 'Cozy indie, acoustic, and lo-fi tracks with introspective lyrics perfect for watching rain through the window',
    icon: CloudRain,
    genre: 'Indie',
    gradient: 'bg-gradient-to-br from-slate-400 via-gray-500 to-zinc-600',
    category: 'relax',
  },
  {
    name: 'Party Vibes',
    prompt: 'Upbeat pop, dance, and hip-hop bangers with infectious hooks and danceable rhythms to keep the party going',
    icon: PartyPopper,
    genre: 'Pop',
    gradient: 'bg-gradient-to-br from-purple-400 via-fuchsia-500 to-pink-600',
    category: 'social',
  },
  {
    name: 'Study Focus',
    prompt: 'Instrumental lo-fi, ambient, and classical music with minimal lyrics to maintain deep concentration and productivity',
    icon: BookOpen,
    genre: 'Lo-fi',
    gradient: 'bg-gradient-to-br from-green-400 via-emerald-500 to-teal-600',
    category: 'focus',
  },
  {
    name: 'Road Trip',
    prompt: 'Classic rock, indie, and feel-good pop anthems with sing-along choruses perfect for long drives and open highways',
    icon: Car,
    genre: 'Rock',
    gradient: 'bg-gradient-to-br from-orange-400 via-amber-500 to-yellow-600',
    category: 'activity',
  },
  {
    name: 'Meditation',
    prompt: 'Peaceful ambient, nature sounds, and gentle instrumental music designed for mindfulness, yoga, and deep relaxation',
    icon: Sparkles,
    genre: 'Ambient',
    gradient: 'bg-gradient-to-br from-purple-400 via-indigo-500 to-blue-600',
    category: 'relax',
  },
  {
    name: 'Running',
    prompt: 'Energetic electronic and pop tracks with steady 140-180 BPM tempo to match running pace and maintain momentum',
    icon: Zap,
    genre: 'Electronic',
    gradient: 'bg-gradient-to-br from-cyan-400 via-blue-500 to-purple-600',
    category: 'activity',
  },
  {
    name: 'Romantic Evening',
    prompt: 'Smooth R&B, soul, and romantic ballads with intimate vocals perfect for candlelit dinners and special moments',
    icon: Heart,
    genre: 'R&B',
    gradient: 'bg-gradient-to-br from-pink-400 via-rose-500 to-red-500',
    category: 'relax',
  },
  {
    name: 'Sleep Time',
    prompt: 'Ultra-calming ambient soundscapes, soft piano, and gentle nature sounds to help drift into peaceful sleep',
    icon: Moon,
    genre: 'Ambient',
    gradient: 'bg-gradient-to-br from-indigo-500 via-purple-600 to-pink-600',
    category: 'relax',
  },
  {
    name: 'Rock Out',
    prompt: 'Powerful classic rock, alternative, and modern rock with epic guitar riffs and anthemic choruses to headbang to',
    icon: Guitar,
    genre: 'Rock',
    gradient: 'bg-gradient-to-br from-red-500 via-orange-600 to-yellow-600',
    category: 'energy',
  },
  {
    name: 'Night Drive',
    prompt: 'Atmospheric synthwave, chillwave, and downtempo electronic with moody vibes for late-night city cruising',
    icon: Moon,
    genre: 'Electronic',
    gradient: 'bg-gradient-to-br from-indigo-600 via-purple-700 to-pink-700',
    category: 'activity',
  },
  {
    name: 'Coffee Shop',
    prompt: 'Laid-back acoustic, bossa nova, and mellow indie folk creating a cozy café atmosphere perfect for reading or chatting',
    icon: Coffee,
    genre: 'Acoustic',
    gradient: 'bg-gradient-to-br from-amber-500 via-orange-600 to-red-600',
    category: 'relax',
  },
  {
    name: 'Gaming Session',
    prompt: 'Epic orchestral, electronic, and rock tracks with intense energy to enhance focus during competitive gaming',
    icon: Gamepad2,
    genre: 'Electronic',
    gradient: 'bg-gradient-to-br from-purple-500 via-pink-600 to-red-600',
    category: 'focus',
  },
  {
    name: 'Beach Vibes',
    prompt: 'Tropical house, reggae, and surf rock with sunny, carefree energy perfect for beach days and summer memories',
    icon: Waves,
    genre: 'Pop',
    gradient: 'bg-gradient-to-br from-cyan-400 via-blue-500 to-teal-600',
    category: 'relax',
  },
  {
    name: 'Dramatic Feels',
    prompt: 'Emotional indie, alternative, and cinematic tracks with powerful vocals and sweeping arrangements for deep feelings',
    icon: Sparkles,
    genre: 'Indie',
    gradient: 'bg-gradient-to-br from-slate-500 via-purple-600 to-indigo-700',
    category: 'relax',
  },
  {
    name: 'Chill Evening',
    prompt: 'Mellow downtempo, chillhop, and ambient beats with smooth vibes perfect for unwinding after a long day',
    icon: Cloud,
    genre: 'Lo-fi',
    gradient: 'bg-gradient-to-br from-blue-400 via-purple-500 to-indigo-600',
    category: 'relax',
  },
  {
    name: 'Upbeat Energy',
    prompt: 'Fast-paced pop, electronic, and funk with infectious grooves and uplifting melodies to boost your mood and energy',
    icon: Zap,
    genre: 'Electronic',
    gradient: 'bg-gradient-to-br from-yellow-400 via-orange-500 to-red-600',
    category: 'energy',
  },
  {
    name: 'Jazz Lounge',
    prompt: 'Sophisticated jazz standards, bebop, and smooth jazz with complex harmonies perfect for elegant gatherings',
    icon: Music,
    genre: 'Jazz',
    gradient: 'bg-gradient-to-br from-amber-600 via-orange-700 to-red-700',
    category: 'social',
  },
  {
    name: 'Dance Party',
    prompt: 'High-energy house, techno, and dance-pop with pulsing basslines and drops that make you want to move',
    icon: PartyPopper,
    genre: 'Dance',
    gradient: 'bg-gradient-to-br from-pink-400 via-purple-500 to-indigo-600',
    category: 'social',
  },
  {
    name: 'Work Productive',
    prompt: 'Minimal techno, ambient electronic, and post-rock instrumentals that enhance focus without being distracting',
    icon: BookOpen,
    genre: 'Ambient',
    gradient: 'bg-gradient-to-br from-blue-400 via-green-500 to-emerald-600',
    category: 'focus',
  },
  {
    name: 'Sunny Bright',
    prompt: 'Cheerful indie pop, feel-good acoustic, and bright electronic with optimistic lyrics and warm melodies',
    icon: Sun,
    genre: 'Pop',
    gradient: 'bg-gradient-to-br from-yellow-300 via-orange-400 to-red-500',
    category: 'social',
  },
  {
    name: 'Peaceful Morning',
    prompt: 'Gentle acoustic guitar, soft piano, and nature-inspired ambient sounds to start your day with tranquility',
    icon: Coffee,
    genre: 'Acoustic',
    gradient: 'bg-gradient-to-br from-orange-300 via-amber-400 to-yellow-500',
    category: 'relax',
  },
  {
    name: 'Calm & Serene',
    prompt: 'Soothing ambient pads, gentle piano, and ethereal soundscapes designed to reduce stress and promote inner peace',
    icon: Cloud,
    genre: 'Ambient',
    gradient: 'bg-gradient-to-br from-blue-300 via-cyan-400 to-teal-500',
    category: 'relax',
  },
  {
    name: 'Electronic Beats',
    prompt: 'Modern electronic, synthwave, and future bass with innovative production and catchy digital melodies',
    icon: Headphones,
    genre: 'Electronic',
    gradient: 'bg-gradient-to-br from-cyan-400 via-blue-500 to-purple-600',
    category: 'energy',
  },
  {
    name: 'Happy Joy',
    prompt: 'Bubbly pop, uplifting house, and feel-good indie with positive vibes and smile-inducing hooks',
    icon: Sun,
    genre: 'Pop',
    gradient: 'bg-gradient-to-br from-pink-400 via-yellow-500 to-orange-600',
    category: 'social',
  },
  {
    name: 'Love Songs',
    prompt: 'Tender love ballads, romantic soul, and heartfelt acoustic tracks celebrating romance and connection',
    icon: Heart,
    genre: 'Soul',
    gradient: 'bg-gradient-to-br from-rose-400 via-pink-500 to-purple-600',
    category: 'relax',
  },
  {
    name: 'Melancholy Mood',
    prompt: 'Introspective singer-songwriter, sad indie, and emotional piano pieces for processing deeper emotions',
    icon: CloudRain,
    genre: 'Indie',
    gradient: 'bg-gradient-to-br from-gray-400 via-slate-500 to-indigo-600',
    category: 'relax',
  },
  {
    name: 'Adventure Awaits',
    prompt: 'Epic folk, anthemic rock, and cinematic instrumentals with soaring melodies perfect for outdoor adventures',
    icon: Mountain,
    genre: 'Rock',
    gradient: 'bg-gradient-to-br from-green-400 via-teal-500 to-blue-600',
    category: 'activity',
  },
  {
    name: 'Travel Explorer',
    prompt: 'World music, exotic rhythms, and culturally diverse tracks that transport you to distant lands and cultures',
    icon: Plane,
    genre: 'World',
    gradient: 'bg-gradient-to-br from-blue-400 via-green-500 to-yellow-600',
    category: 'activity',
  },
  {
    name: 'Techno Underground',
    prompt: 'Dark techno, industrial, and minimal electronic with hypnotic rhythms and deep basslines for late-night sessions',
    icon: Headphones,
    genre: 'Techno',
    gradient: 'bg-gradient-to-br from-purple-600 via-indigo-700 to-black',
    category: 'energy',
  },
  {
    name: 'Nature & Zen',
    prompt: 'Organic ambient, forest sounds, and meditative drones blending music with natural soundscapes for grounding',
    icon: Sparkles,
    genre: 'Ambient',
    gradient: 'bg-gradient-to-br from-green-300 via-emerald-400 to-teal-500',
    category: 'relax',
  },
  {
    name: 'Fun & Quirky',
    prompt: 'Playful indie pop, whimsical folk, and eccentric electronic with unusual instruments and creative arrangements',
    icon: Music,
    genre: 'Indie',
    gradient: 'bg-gradient-to-br from-pink-400 via-purple-500 to-indigo-600',
    category: 'social',
  },
  {
    name: 'City Night Life',
    prompt: 'Urban hip-hop, R&B, and contemporary electronic capturing the pulse and energy of nighttime city streets',
    icon: CircleDot,
    genre: 'Hip-Hop',
    gradient: 'bg-gradient-to-br from-orange-500 via-red-600 to-purple-700',
    category: 'energy',
  },
  {
    name: 'Tropical Paradise',
    prompt: 'Caribbean rhythms, Latin beats, and island vibes with steel drums and sunny grooves for vacation mode',
    icon: Palmtree,
    genre: 'Reggae',
    gradient: 'bg-gradient-to-br from-yellow-400 via-orange-500 to-red-500',
    category: 'relax',
  },
];

/**
 * Get mood templates filtered by category
 */
export function getMoodTemplatesByCategory(
  category: MoodTemplate['category']
): MoodTemplate[] {
  return MOOD_TEMPLATES.filter((template) => template.category === category);
}

/**
 * Get a random selection of mood templates
 */
export function getRandomMoodTemplates(count: number = 6): MoodTemplate[] {
  const shuffled = [...MOOD_TEMPLATES].sort(() => 0.5 - Math.random());
  return shuffled.slice(0, count);
}
