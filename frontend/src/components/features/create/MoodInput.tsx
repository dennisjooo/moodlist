'use client';

import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Textarea } from '@/components/ui/textarea';
import { MoodInputSkeleton } from '@/components/shared/LoadingStates';
import { MOOD_TEMPLATES } from '@/lib/constants/moodTemplates';
import { shuffleArray } from '@/lib/utils/array';
import { useEffect, useState, useMemo } from 'react';

interface MoodInputProps {
  onSubmit?: (mood: string) => void;
  initialMood?: string;
  disabled?: boolean;
  loading?: boolean;
}

export default function MoodInput({ onSubmit, initialMood, disabled = false, loading = false }: MoodInputProps) {
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

  const moodExamples = useMemo(() => shuffleArray(MOOD_TEMPLATES).slice(0, 6), []);

  // Show skeleton while loading
  if (loading) {
    return <MoodInputSkeleton />;
  }

  return (
    <Card className="w-full border-0 shadow-lg">
      <CardContent className="p-6">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Textarea
              placeholder="Describe your mood..."
              value={mood}
              onChange={(e) => setMood(e.target.value)}
              disabled={disabled}
              className="min-h-[120px] resize-none border-0 bg-muted/50 text-base placeholder:text-muted-foreground/60 focus-visible:ring-1"
            />
          </div>

          <div className="flex flex-wrap gap-1.5 justify-center sm:justify-start">
            {moodExamples.map((template) => (
              <button
                key={template.name}
                type="button"
                onClick={() => setMood(template.prompt)}
                disabled={disabled}
                className="px-2.5 py-1 text-xs bg-muted hover:bg-muted/80 rounded-md transition-colors text-muted-foreground hover:text-foreground disabled:cursor-not-allowed"
              >
                {template.name}
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

