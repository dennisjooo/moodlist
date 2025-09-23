// Utility function to generate gradient colors based on mood keywords
export function generateMoodGradient(mood: string): string {
  const moodLower = mood.toLowerCase();
  
  // Define color mappings based on mood keywords
  const colorMappings = {
    // Calm/Relaxing moods
    chill: 'bg-gradient-to-br from-blue-400 via-purple-500 to-indigo-600',
    relax: 'bg-gradient-to-br from-blue-300 via-cyan-400 to-teal-500',
    peaceful: 'bg-gradient-to-br from-green-300 via-blue-400 to-purple-500',
    calm: 'bg-gradient-to-br from-slate-400 via-blue-400 to-indigo-500',
    evening: 'bg-gradient-to-br from-purple-400 via-indigo-500 to-blue-600',
    night: 'bg-gradient-to-br from-indigo-500 via-purple-600 to-pink-600',
    
    // Energetic moods
    energy: 'bg-gradient-to-br from-red-400 via-pink-500 to-rose-600',
    workout: 'bg-gradient-to-br from-orange-400 via-red-500 to-pink-600',
    party: 'bg-gradient-to-br from-purple-400 via-fuchsia-500 to-pink-600',
    dance: 'bg-gradient-to-br from-pink-400 via-purple-500 to-indigo-600',
    upbeat: 'bg-gradient-to-br from-yellow-400 via-orange-500 to-red-600',
    
    // Focus/Study moods
    focus: 'bg-gradient-to-br from-green-400 via-emerald-500 to-teal-600',
    study: 'bg-gradient-to-br from-emerald-400 via-green-500 to-cyan-600',
    work: 'bg-gradient-to-br from-blue-400 via-green-500 to-emerald-600',
    productive: 'bg-gradient-to-br from-teal-400 via-green-500 to-blue-600',
    
    // Happy/Positive moods
    happy: 'bg-gradient-to-br from-yellow-400 via-orange-500 to-pink-600',
    joy: 'bg-gradient-to-br from-pink-400 via-yellow-500 to-orange-600',
    sunny: 'bg-gradient-to-br from-yellow-300 via-orange-400 to-red-500',
    bright: 'bg-gradient-to-br from-cyan-400 via-yellow-500 to-orange-600',
    
    // Romantic moods
    romantic: 'bg-gradient-to-br from-pink-400 via-rose-500 to-red-500',
    love: 'bg-gradient-to-br from-rose-400 via-pink-500 to-purple-600',
    
    // Sad/Melancholic moods
    sad: 'bg-gradient-to-br from-slate-400 via-gray-500 to-blue-600',
    melancholy: 'bg-gradient-to-br from-gray-400 via-slate-500 to-indigo-600',
    rainy: 'bg-gradient-to-br from-slate-400 via-gray-500 to-zinc-600',
    
    // Adventure/Travel moods
    adventure: 'bg-gradient-to-br from-orange-400 via-amber-500 to-yellow-600',
    travel: 'bg-gradient-to-br from-green-400 via-teal-500 to-blue-600',
    road: 'bg-gradient-to-br from-orange-400 via-amber-500 to-yellow-600',
    trip: 'bg-gradient-to-br from-blue-400 via-green-500 to-yellow-600',
    
    // Morning/Coffee moods
    morning: 'bg-gradient-to-br from-amber-400 via-orange-500 to-red-500',
    coffee: 'bg-gradient-to-br from-amber-500 via-orange-600 to-red-600',
    
    // Jazz/Sophisticated moods
    jazz: 'bg-gradient-to-br from-amber-400 via-orange-500 to-red-500',
    sophisticated: 'bg-gradient-to-br from-slate-500 via-gray-600 to-zinc-700',
    
    // Electronic/Modern moods
    electronic: 'bg-gradient-to-br from-cyan-400 via-blue-500 to-purple-600',
    techno: 'bg-gradient-to-br from-purple-400 via-pink-500 to-red-600',
    
    // Default fallbacks
    default: 'bg-gradient-to-br from-gray-400 via-slate-500 to-zinc-600',
  };
  
  // Check for keyword matches
  for (const [keyword, gradient] of Object.entries(colorMappings)) {
    if (moodLower.includes(keyword)) {
      return gradient;
    }
  }
  
  // If no keyword matches, generate a gradient based on string hash
  return generateHashBasedGradient(mood);
}

// Generate gradient based on string hash for unique moods
function generateHashBasedGradient(text: string): string {
  const hash = text.split('').reduce((acc, char) => {
    return char.charCodeAt(0) + ((acc << 5) - acc);
  }, 0);
  
  const gradients = [
    'bg-gradient-to-br from-blue-400 via-purple-500 to-indigo-600',
    'bg-gradient-to-br from-red-400 via-pink-500 to-rose-600',
    'bg-gradient-to-br from-green-400 via-emerald-500 to-teal-600',
    'bg-gradient-to-br from-orange-400 via-amber-500 to-yellow-600',
    'bg-gradient-to-br from-pink-400 via-rose-500 to-red-500',
    'bg-gradient-to-br from-purple-400 via-fuchsia-500 to-pink-600',
    'bg-gradient-to-br from-cyan-400 via-blue-500 to-purple-600',
    'bg-gradient-to-br from-emerald-400 via-green-500 to-cyan-600',
    'bg-gradient-to-br from-amber-400 via-orange-500 to-red-500',
    'bg-gradient-to-br from-slate-400 via-gray-500 to-zinc-600',
  ];
  
  return gradients[Math.abs(hash) % gradients.length];
}

// Helper function to get mood-appropriate genre
export function getMoodGenre(mood: string): string {
  const moodLower = mood.toLowerCase();
  
  const genreMappings = {
    chill: 'Lo-fi',
    relax: 'Ambient',
    energy: 'Electronic',
    workout: 'EDM',
    party: 'Pop',
    focus: 'Ambient',
    study: 'Classical',
    romantic: 'R&B',
    jazz: 'Jazz',
    rock: 'Rock',
    electronic: 'Electronic',
    dance: 'Dance',
    sad: 'Indie',
    happy: 'Pop',
    morning: 'Jazz',
    coffee: 'Acoustic',
    rainy: 'Indie',
    adventure: 'Rock',
    travel: 'World',
  };
  
  for (const [keyword, genre] of Object.entries(genreMappings)) {
    if (moodLower.includes(keyword)) {
      return genre;
    }
  }
  
  return 'Mixed';
}