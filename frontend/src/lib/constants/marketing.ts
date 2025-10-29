import type { LucideIcon } from 'lucide-react';
import { Brain, MessageCircle, Music, Sunrise, Sunset, PartyPopper } from 'lucide-react';

export interface FAQItem {
  question: string;
  answer: string;
}

export interface HowItWorksStep {
  icon: LucideIcon;
  title: string;
  description: string;
  color: string;
}

export interface MoodIdea {
  title: string;
  tagline: string;
  description: string;
  prompt: string;
  accent: string;
  icon: LucideIcon;
}

export const CTA_HIGHLIGHTS = [
  'Curated by AI with your emotions in mind',
  'Instantly saved to your Spotify library',
  'Tweak every playlist and keep the vibe',
] as const;

export const FAQ_ITEMS: FAQItem[] = [
  {
    question: 'Do I need a premium Spotify account?',
    answer:
      "Moodlist works best with a Spotify Premium account so your playlists can be saved automatically. You can still explore moods and prompts with a free account—when you're ready, connect Premium to unlock instant syncing.",
  },
  {
    question: 'What kind of prompts should I write?',
    answer:
      'Describe the atmosphere you want to create. Mention emotions, locations, energy levels, or artists you like. The more detail you give, the more accurate the AI becomes at matching tracks to your moment.',
  },
  {
    question: 'Can I edit the playlist after it is generated?',
    answer:
      'Absolutely. Once the playlist is in your Spotify library you can reorder songs, add new tracks, or remove anything that does not fit. Moodlist is designed to give you a thoughtful starting point.',
  },
  {
    question: 'Is my data safe?',
    answer:
      'We only request the permissions required to create playlists on your behalf. Your listening history stays on Spotify—Moodlist never stores or shares your personal data.',
  },
];

export const HOW_IT_WORKS_STEPS: HowItWorksStep[] = [
  {
    icon: MessageCircle,
    title: 'Describe Your Mood',
    description:
      "Tell us how you're feeling in your own words — happy, melancholic, energetic, or anything in between.",
    color: 'from-blue-500 to-purple-600',
  },
  {
    icon: Brain,
    title: 'AI Analyzes & Understands',
    description:
      'Our advanced AI processes your mood and matches it with musical characteristics and genres.',
    color: 'from-purple-600 to-pink-600',
  },
  {
    icon: Music,
    title: 'Spotify Creates Your Playlist',
    description:
      'A personalized playlist is generated and saved directly to your Spotify account, ready to play.',
    color: 'from-pink-600 to-green-500',
  },
];

export const MOOD_IDEAS: MoodIdea[] = [
  {
    title: 'Sunrise Reset',
    tagline: 'Morning ritual',
    description: 'Ease into the day with warmth and clarity.',
    prompt:
      'Create a sunrise playlist with gentle electronic and acoustic tracks that build energy without overpowering vocals.',
    accent: 'from-amber-400/80 via-orange-500/80 to-rose-500/60',
    icon: Sunrise,
  },
  {
    title: 'Deep Focus Flow',
    tagline: 'Heads-down work',
    description: 'Stay locked-in during long work sessions.',
    prompt:
      'Generate an instrumental mix that blends downtempo beats with atmospheric synths around 90 BPM.',
    accent: 'from-sky-400/80 via-blue-500/80 to-indigo-500/60',
    icon: Brain,
  },
  {
    title: 'Slow Evening',
    tagline: 'Unwind time',
    description: 'Wind down after a packed day.',
    prompt:
      'Give me soulful R&B and soft jazz perfect for a rainy evening and a glass of wine.',
    accent: 'from-purple-400/80 via-violet-500/80 to-fuchsia-500/60',
    icon: Sunset,
  },
  {
    title: 'Movement Boost',
    tagline: 'Workout energy',
    description: 'Boost energy for a midday workout.',
    prompt:
      'Build a high-energy pop and hip-hop playlist between 120-130 BPM that keeps motivation high.',
    accent: 'from-emerald-400/80 via-teal-500/80 to-cyan-500/60',
    icon: Music,
  },
  {
    title: 'Creative Sparks',
    tagline: 'Ideation fuel',
    description: 'Soundtrack for brainstorming sessions.',
    prompt:
      'Mix experimental electronic and indie tracks that feel curious, playful, and lyric-light.',
    accent: 'from-pink-400/80 via-rose-500/80 to-orange-500/60',
    icon: MessageCircle,
  },
  {
    title: 'Weekend Gathering',
    tagline: 'Friends night',
    description: 'Kick off a laid-back hang with friends.',
    prompt:
      'Curate upbeat disco, nu-funk, and house grooves that make conversation feel effortless.',
    accent: 'from-lime-400/80 via-emerald-500/80 to-teal-500/60',
    icon: PartyPopper,
  },
];
