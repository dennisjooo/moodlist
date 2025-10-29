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

export const FEATURED_MOOD_SHOWCASES: FeaturedMoodShowcase[] = [
  {
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
  },
  {
    name: 'Rainy Evening Serenity',
    prompt: 'chill rainy evening',
    moodInterpretation:
      'The user desires music suitable for a quiet, introspective, and relaxing evening indoors while it is raining. The atmosphere should be calm, slightly melancholic, cozy, and non-intrusive.',
    primaryEmotion: 'Calmness, Nostalgia, Serenity',
    energyLevel: 'Low and Mellow',
    summaryHighlights: [
      'Soft acoustic textures and gentle instrumentation',
      'Slow tempos between 50-95 BPM for contemplation',
      'Low energy levels that encourage relaxation',
    ],
    keywords: ['rainy day', 'ambient', 'acoustic', 'downtempo'],
    colorScheme: {
      primary: '#607D8B',
      secondary: '#8B6078',
      tertiary: '#788B60',
    },
  },
  {
    name: 'Workout Intensity',
    prompt: 'energetic workout',
    moodInterpretation:
      'The user desires high-intensity, motivating music suitable for physical exertion, such as running, lifting weights, or HIIT. The music needs a driving rhythm, high energy, and a strong, forward momentum.',
    primaryEmotion: 'Motivation/Excitement',
    energyLevel: 'Very High',
    summaryHighlights: [
      'Maximum energy levels to fuel intense activity',
      'Fast tempos between 128-175 BPM for optimal workout pace',
      'High danceability to keep movements synchronized',
    ],
    keywords: ['workout', 'high energy', 'motivational', 'EDM'],
    colorScheme: {
      primary: '#FF4136',
      secondary: '#39FF14',
      tertiary: '#1199FF',
    },
  },
  {
    name: 'Late Night Groove',
    prompt:
      "songs that sound like late-night French funk — smooth, retro, confident, and dripping with groove. Think Dabeull, FKJ, Breakbot, and a bit of Daft Punk's charm.",
    moodInterpretation:
      'The user is seeking music that evokes the atmosphere of late-night cruising or sophisticated urban environments, characterized by smooth, retro electronic funk and nu-disco influences.',
    primaryEmotion: 'Confidence and Cool Sophistication',
    energyLevel: 'Moderate to High Groove',
    summaryHighlights: [
      'Smooth electronic funk with retro production',
      'Balanced energy between 0.6-0.85 for sustained groove',
      'High instrumentalness featuring synthesizers and samples',
    ],
    keywords: ['french funk', 'nu-disco', 'smooth groove', 'retro electronic'],
    colorScheme: {
      primary: '#CC3366',
      secondary: '#33CC99',
      tertiary: '#6633CC',
    },
  },
  {
    name: 'Romantic Evening',
    prompt: 'romantic dinner',
    moodInterpretation:
      'The user desires intimate, sophisticated music suitable for a romantic dinner setting. The atmosphere should be warm, emotional, and conducive to connection.',
    primaryEmotion: 'Romance and Intimacy',
    energyLevel: 'Moderate and Warm',
    summaryHighlights: [
      'Smooth, emotive vocals and gentle instrumentation',
      'Moderate tempo and energy for relaxed ambiance',
      'High valence with emotional depth for romantic connection',
    ],
    keywords: ['romantic', 'intimate', 'dinner', 'sophisticated'],
    colorScheme: {
      primary: '#D2691E',
      secondary: '#8B4513',
      tertiary: '#CD853F',
    },
  },
];

export const FEATURED_MOOD_FEATURES_ARRAYS: FeatureMetric[][] = [
  // Confidence Kickoff
  [
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
  ],
  // Rainy Evening Serenity
  [
    {
      label: 'Energy',
      range: [0.1, 0.4],
      description: 'Gentle and calming for quiet contemplation.',
    },
    {
      label: 'Acousticness',
      range: [0.5, 1.0],
      description: 'Rich acoustic textures create cozy atmosphere.',
    },
    {
      label: 'Tempo',
      range: [50, 95],
      unit: 'BPM',
      description: 'Slow pace perfect for relaxed introspection.',
    },
    {
      label: 'Loudness',
      range: [-25, -12],
      unit: 'dB',
      description: 'Soft volume that doesn\'t intrude on quiet moments.',
    },
    {
      label: 'Instrumentalness',
      range: [0.2, 0.8],
      description: 'Balance of vocals and instrumentation for gentle ambiance.',
    },
  ],
  // Workout Intensity
  [
    {
      label: 'Energy',
      range: [0.8, 1.0],
      description: 'Maximum power to fuel intense physical exertion.',
    },
    {
      label: 'Tempo',
      range: [128, 175],
      unit: 'BPM',
      description: 'Fast pace optimized for workout rhythm and motivation.',
    },
    {
      label: 'Danceability',
      range: [0.6, 1.0],
      description: 'Highly danceable beats to synchronize movement.',
    },
    {
      label: 'Loudness',
      range: [-7, -2],
      unit: 'dB',
      description: 'Punchy mix that cuts through gym noise.',
    },
    {
      label: 'Valence',
      range: [0.6, 1.0],
      description: 'Uplifting positivity to maintain motivation.',
    },
  ],
  // Late Night Groove
  [
    {
      label: 'Energy',
      range: [0.6, 0.85],
      description: 'Balanced groove that sustains late-night momentum.',
    },
    {
      label: 'Danceability',
      range: [0.65, 0.95],
      description: 'Smooth, confident rhythm for sophisticated movement.',
    },
    {
      label: 'Instrumentalness',
      range: [0.3, 0.8],
      description: 'Rich electronic textures and retro production.',
    },
    {
      label: 'Tempo',
      range: [105, 128],
      unit: 'BPM',
      description: 'Perfect pace for late-night cruising and groove.',
    },
    {
      label: 'Valence',
      range: [0.6, 0.9],
      description: 'Cool confidence with positive, sophisticated energy.',
    },
  ],
  // Romantic Evening
  [
    {
      label: 'Energy',
      range: [0.2, 0.6],
      description: 'Warm and intimate energy for emotional connection.',
    },
    {
      label: 'Valence',
      range: [0.4, 0.8],
      description: 'Emotional depth with gentle positivity.',
    },
    {
      label: 'Danceability',
      range: [0.3, 0.7],
      description: 'Subtle rhythm that encourages closeness.',
    },
    {
      label: 'Acousticness',
      range: [0.3, 0.9],
      description: 'Natural, emotive instrumentation.',
    },
    {
      label: 'Tempo',
      range: [70, 120],
      unit: 'BPM',
      description: 'Comfortable pace for intimate conversation.',
    },
  ],
];

export const FEATURED_MOOD_TRACKS_ARRAYS: FeaturedTrack[][] = [
  // Confidence Kickoff
  [
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
  ],
  // Rainy Evening Serenity
  [
    {
      name: 'Master of None',
      artists: 'Beach House',
      energy: 0.344,
      danceability: 0.492,
      valence: 0.247,
      tempo: 86.485,
      highlight: 'Dreamy, atmospheric sound perfect for rainy contemplation.',
      spotifyUri: 'spotify:track:3stWWPN41byqp8loPdy92u',
    },
    {
      name: 'Blue Light',
      artists: 'Mazzy Star',
      energy: 0.223,
      danceability: 0.457,
      valence: 0.181,
      tempo: 135.46,
      highlight: 'Hauntingly beautiful with gentle, ethereal vocals.',
      spotifyUri: 'spotify:track:3BdHMOIA9B0bN53jbE5nWe',
    },
    {
      name: 'My Foolish Heart',
      artists: 'Bill Evans Trio',
      energy: 0.121,
      danceability: 0.395,
      valence: 0.138,
      tempo: 114.396,
      highlight: 'Intimate jazz piano that soothes the rainy evening mood.',
      spotifyUri: 'spotify:track:6yKkA8HzwWTZ5taIMaG4Nm',
    },
  ],
  // Workout Intensity
  [
    {
      name: 'Gotchu',
      artists: 'Justin Jay',
      energy: 0.744,
      danceability: 0.843,
      valence: 0.418,
      tempo: 125.049,
      highlight: 'High-energy electronic beats to power through any workout.',
      spotifyUri: 'spotify:track:2n93nPN4lMaaIm6YJEsX5E',
    },
    {
      name: 'In The Middle',
      artists: 'YouNotUs, Plastik Funk',
      energy: 0.85,
      danceability: 0.78,
      valence: 0.75,
      tempo: 126.0,
      highlight: 'Driving EDM rhythm that keeps the intensity high.',
      spotifyUri: 'spotify:track:0OW3s0JdsWXYGCw6PLU53x',
    },
    {
      name: 'Animals',
      artists: 'Martin Garrix',
      energy: 0.95,
      danceability: 0.65,
      valence: 0.8,
      tempo: 128.0,
      highlight: 'Explosive drops and maximum energy for peak performance.',
      spotifyUri: 'spotify:track:5eQx3MJ6FMM6h8kgN0e8tW',
    },
  ],
  // Late Night Groove
  [
    {
      name: 'The Less I Know The Better',
      artists: 'Tame Impala',
      energy: 0.74,
      danceability: 0.64,
      valence: 0.785,
      tempo: 116.879,
      highlight: 'Psychedelic groove with confident, retro electronic charm.',
      spotifyUri: 'spotify:track:6K4t31amVTZDgR3sKmwUJJ',
    },
    {
      name: "Don't Forget It",
      artists: 'Dabeull, Jordan Lee',
      energy: 0.69,
      danceability: 0.838,
      valence: 0.776,
      tempo: 77.936,
      highlight: 'Smooth French funk with irresistible groove.',
      spotifyUri: 'spotify:track:6GVrDwaAuGOida6c7eYjLl',
    },
    {
      name: 'Inspector Norse',
      artists: 'Todd Terje',
      energy: 0.782,
      danceability: 0.912,
      valence: 0.89,
      tempo: 119.979,
      highlight: 'Nu-disco brilliance with sophisticated electronic production.',
      spotifyUri: 'spotify:track:1NHd4UVxT5d5EGYzlDq17T',
    },
  ],
  // Romantic Evening
  [
    {
      name: 'At Last',
      artists: 'Etta James',
      energy: 0.35,
      danceability: 0.45,
      valence: 0.65,
      tempo: 87.0,
      highlight: 'Timeless romance with emotive, soulful vocals.',
      spotifyUri: 'spotify:track:4U45aEWtQhrm8A5mxPaFZ7',
    },
    {
      name: 'Lover',
      artists: 'Taylor Swift',
      energy: 0.45,
      danceability: 0.55,
      valence: 0.7,
      tempo: 68.0,
      highlight: 'Intimate ballad perfect for romantic connection.',
      spotifyUri: 'spotify:track:1dGr1c8CrMLDpV6mPbImSI',
    },
    {
      name: 'Fly Me To The Moon',
      artists: 'Frank Sinatra',
      energy: 0.25,
      danceability: 0.6,
      valence: 0.75,
      tempo: 119.0,
      highlight: 'Classic romance with smooth, sophisticated charm.',
      spotifyUri: 'spotify:track:7FXj7Qg3YQ TbKl5VKi8Fj',
    },
  ],
];
