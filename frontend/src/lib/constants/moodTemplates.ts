/**
 * Curated mood templates for quick playlist creation
 * These templates help onboard new users and provide inspiration
 */

export interface MoodTemplate {
  emoji: string;
  name: string;
  prompt: string;
  category?: 'energy' | 'focus' | 'relax' | 'social' | 'activity';
}

export const MOOD_TEMPLATES: MoodTemplate[] = [
  {
    emoji: '🌅',
    name: 'Morning Coffee',
    prompt: 'Chill morning vibes to start my day',
    category: 'relax',
  },
  {
    emoji: '💪',
    name: 'Workout Energy',
    prompt: 'High-energy workout music to get pumped',
    category: 'energy',
  },
  {
    emoji: '🌧️',
    name: 'Rainy Day',
    prompt: 'Cozy rainy day acoustic songs',
    category: 'relax',
  },
  {
    emoji: '🎉',
    name: 'Party Vibes',
    prompt: 'Upbeat party music to dance to',
    category: 'social',
  },
  {
    emoji: '📚',
    name: 'Study Focus',
    prompt: 'Focus music for deep work',
    category: 'focus',
  },
  {
    emoji: '🚗',
    name: 'Road Trip',
    prompt: 'Fun road trip anthems',
    category: 'activity',
  },
  {
    emoji: '🧘',
    name: 'Meditation',
    prompt: 'Peaceful meditation and mindfulness music',
    category: 'relax',
  },
  {
    emoji: '🏃',
    name: 'Running',
    prompt: 'Energetic running playlist with steady beats',
    category: 'activity',
  },
  {
    emoji: '💕',
    name: 'Romantic Evening',
    prompt: 'Romantic songs for a special evening',
    category: 'relax',
  },
  {
    emoji: '😴',
    name: 'Sleep Time',
    prompt: 'Calming sleep music and ambient sounds',
    category: 'relax',
  },
  {
    emoji: '🎸',
    name: 'Rock Out',
    prompt: 'Classic and modern rock anthems',
    category: 'energy',
  },
  {
    emoji: '🌃',
    name: 'Night Drive',
    prompt: 'Late night driving vibes with chill beats',
    category: 'activity',
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

/**
 * Format a mood template for display
 */
export function formatMoodTemplate(template: MoodTemplate): string {
  return `${template.emoji} ${template.name}`;
}
