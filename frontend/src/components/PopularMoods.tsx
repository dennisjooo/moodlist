import MoodCard from '@/components/MoodCard';

interface PopularMoodsProps {
  isLoggedIn: boolean;
}

export default function PopularMoods({ isLoggedIn }: PopularMoodsProps) {
  // Now we just need mood names - colors and genres are auto-generated!
  const allMoodExamples = [
    'Chill Evening',
    'Workout Energy',
    'Study Focus',
    'Road Trip',
    'Romantic Night',
    'Morning Coffee',
    'Rainy Day',
    'Party Vibes',
  ];

  // Show only first 4 moods on mobile, all on desktop
  const moodExamples = allMoodExamples;

  if (isLoggedIn) return null;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mt-16">
      <div className="flex flex-col items-center">
        <h2 className="text-2xl font-semibold text-center mb-8">Popular Moods</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6 max-w-6xl w-full">
          {moodExamples.map((mood, index) => {
            // Hide cards beyond index 3 on mobile
            const hiddenOnMobile = index > 3;
            return (
              <MoodCard
                key={index}
                mood={mood}
                onClick={() => console.log(`Selected mood: ${mood}`)}
                className={hiddenOnMobile ? 'hidden md:flex' : ''}
              />
            );
          })}
        </div>
      </div>
    </div>
  );
}