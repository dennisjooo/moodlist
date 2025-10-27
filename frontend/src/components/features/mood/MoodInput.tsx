'use client';

import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Textarea } from '@/components/ui/textarea';
import { useEffect, useState } from 'react';

interface MoodInputProps {
  onSubmit?: (mood: string) => void;
  initialMood?: string;
  disabled?: boolean;
}

export default function MoodInput({ onSubmit, initialMood, disabled = false }: MoodInputProps) {
  const [mood, setMood] = useState(initialMood || '');

  // Update mood when initialMood changes
  useEffect(() => {
    if (initialMood) {
      setMood(initialMood);
    }
  }, [initialMood]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (mood.trim() && onSubmit && !disabled) {
      onSubmit(mood.trim());
    }
  };

  const moodExamples = [
    'chill rainy evening',
    'energetic workout',
    'nostalgic summer',
    'focused work',
    'romantic dinner',
    'morning commute',
  ];

  return (
    <Card className="w-full border-0 shadow-lg">
      <CardContent className="p-6">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Textarea
              placeholder="Describe your mood..."
              value={mood}
              onChange={(e) => setMood(e.target.value)}
              className="min-h-[120px] resize-none border-0 bg-muted/50 text-base placeholder:text-muted-foreground/60 focus-visible:ring-1"
            />
          </div>

          <div className="flex flex-wrap gap-1.5 justify-center sm:justify-start">
            {moodExamples.map((example) => (
              <button
                key={example}
                type="button"
                onClick={() => setMood(example)}
                className="px-2.5 py-1 text-xs bg-muted hover:bg-muted/80 rounded-md transition-colors text-muted-foreground hover:text-foreground"
              >
                {example}
              </button>
            ))}
          </div>

          <Button
            type="submit"
            className="w-full h-9"
            disabled={disabled}
          >
            Generate Playlist
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

