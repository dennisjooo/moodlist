'use client';

import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Textarea } from '@/components/ui/textarea';
import { useState } from 'react';

interface MoodInputProps {
  onSubmit?: (mood: string) => void;
}

export default function MoodInput({ onSubmit }: MoodInputProps) {
  const [mood, setMood] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (mood.trim() && onSubmit) {
      onSubmit(mood.trim());
    }
  };

  const moodExamples = [
    'chill rainy evening',
    'energetic workout',
    'nostalgic summer',
    'focused work',
  ];

  return (
    <Card className="w-full border-0 shadow-lg">
      <CardContent className="p-6">
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="space-y-2">
            <Textarea
              placeholder="Describe your mood..."
              value={mood}
              onChange={(e) => setMood(e.target.value)}
              className="min-h-[120px] resize-none border-0 bg-muted/50 text-base placeholder:text-muted-foreground/60 focus-visible:ring-1"
            />
          </div>
          
          <div className="flex flex-wrap gap-2 justify-center sm:justify-start">
            {moodExamples.map((example) => (
              <button
                key={example}
                type="button"
                onClick={() => setMood(example)}
                className="px-3 py-1.5 text-sm bg-muted hover:bg-muted/80 rounded-md transition-colors text-muted-foreground hover:text-foreground"
              >
                {example}
              </button>
            ))}
          </div>

          <Button
            type="submit"
            className="w-full h-11"
            disabled={!mood.trim()}
          >
            Generate Playlist
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}