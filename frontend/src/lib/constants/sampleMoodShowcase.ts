export interface FeaturedMoodShowcase {
  name: string;
  prompt: string;
  moodInterpretation: string;
  primaryEmotion: string;
  energyLevel: string;
  summaryHighlights: string[];
  keywords: string[];
  colorScheme: {
    primary: string;
    secondary: string;
    tertiary: string;
  };
}

export interface FeatureMetric {
  label: string;
  range: [number, number];
  unit?: string;
  description: string;
}

export interface FeaturedTrack {
  name: string;
  artists: string;
  energy: number;
  danceability: number;
  valence: number;
  tempo: number;
  highlight: string;
  spotifyUri: string;
}

export const FEATURED_MOOD_SHOWCASE: FeaturedMoodShowcase = {
  name: 'Confidence Kickoff',
  prompt:
    "Songs that sound like you're getting ready for the best night of your life — confidence, glitter, and zero doubt.",
  moodInterpretation:
    'The user wants extremely upbeat, assertive dance-pop that radiates glamour and positive swagger before a big night out.',
  primaryEmotion: 'Confidence / Exhilaration',
  energyLevel: 'Very High Intensity',
  summaryHighlights: [
    'Major-key anthems drenched in sparkle and strut',
    'Locked between 120-140 BPM to keep momentum high',
    'Maxed-out valence so every hook screams celebration',
  ],
  keywords: ['confidence anthem', 'glam pop', 'night out', 'bold energy'],
  colorScheme: {
    primary: '#FF1493',
    secondary: '#32CD32',
    tertiary: '#4169E1',
  },
};

export const FEATURED_MOOD_FEATURES: FeatureMetric[] = [
  {
    label: 'Energy',
    range: [0.8, 1.0],
    description: 'Keeps every track surging with maximum drive.',
  },
  {
    label: 'Danceability',
    range: [0.7, 1.0],
    description: 'Built for choreography-level bounce and groove.',
  },
  {
    label: 'Valence',
    range: [0.8, 1.0],
    description: 'Ensures the playlist never drops below full-throttle joy.',
  },
  {
    label: 'Tempo',
    range: [115, 145],
    unit: 'BPM',
    description: 'Locks the pace between runway strut and dance-floor sprint.',
  },
  {
    label: 'Loudness',
    range: [-6, -2],
    unit: 'dB',
    description: 'Keeps the mix punchy enough to dominate the room.',
  },
];

export const FEATURED_MOOD_TRACKS: FeaturedTrack[] = [
  {
    name: 'Levitating (feat. DaBaby)',
    artists: 'Dua Lipa',
    energy: 0.825,
    danceability: 0.702,
    valence: 0.915,
    tempo: 102.977,
    highlight: 'Nu-disco shimmer that sets the confident tone from the jump.',
    spotifyUri: 'spotify:track:5nujrmhLynf4yMoMtj8AQF',
  },
  {
    name: "Beg for You (feat. Rina Sawayama)",
    artists: 'Charli XCX, Rina Sawayama',
    energy: 0.945,
    danceability: 0.788,
    valence: 0.466,
    tempo: 128.036,
    highlight: 'Peak-energy drop that feels like the glitter cannon moment.',
    spotifyUri: 'spotify:track:11M8c9SHQYpd8DOrmcu25k',
  },
  {
    name: 'Where Have You Been',
    artists: 'Rihanna',
    energy: 0.847,
    danceability: 0.719,
    valence: 0.443,
    tempo: 127.96,
    highlight: 'Relentless pulse that keeps the momentum locked in.',
    spotifyUri: 'spotify:track:5WQQIDU3HRaMyPkob8mpFb',
  },
];
