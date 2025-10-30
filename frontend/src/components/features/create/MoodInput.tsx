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
    <div className="relative animate-in fade-in duration-500">
      <div
        aria-hidden="true"
        className="absolute inset-0 -z-10 rounded-3xl bg-gradient-to-br from-primary/30 via-primary/10 to-transparent opacity-70 blur-3xl"
      />
      <Card className="w-full overflow-hidden rounded-3xl border border-border/40 bg-background/80 shadow-[0_25px_60px_-30px_rgba(15,23,42,0.45)] backdrop-blur-xl">
        <CardContent className="p-5 sm:p-6">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-muted-foreground">Tell us about the moment</span>
                <span className="text-xs text-muted-foreground/70">Be as specific as you like</span>
              </div>
              <Textarea
                placeholder="e.g. Late-night coding session with lo-fi beats and a splash of energy"
                value={mood}
                onChange={(e) => setMood(e.target.value)}
                disabled={disabled}
                className="min-h-[100px] resize-none rounded-2xl border border-border/50 bg-muted/40 px-4 py-3 text-base shadow-inner focus-visible:border-primary/60 focus-visible:ring-2 focus-visible:ring-primary/40"
              />
            </div>

            <div className="space-y-2">
              <span className="block text-xs font-semibold uppercase tracking-[0.3em] text-muted-foreground/80">
                Try a preset
              </span>
              <div className="flex flex-wrap justify-center gap-2 sm:justify-start">
                {moodExamples.map((template) => (
                  <button
                    key={template.name}
                    type="button"
                    onClick={() => setMood(template.prompt)}
                    disabled={disabled}
                    className="rounded-full border border-transparent bg-muted/60 px-3 py-1.5 text-xs font-medium text-muted-foreground transition-all hover:-translate-y-0.5 hover:border-primary/40 hover:bg-background/80 hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 disabled:cursor-not-allowed"
                  >
                    {template.name}
                  </button>
                ))}
              </div>
            </div>

            <Button
              type="submit"
              className="h-10 w-full rounded-full bg-gradient-to-r from-primary to-primary/70 text-base font-semibold shadow-lg shadow-primary/20 transition hover:brightness-110 focus-visible:ring-2 focus-visible:ring-primary/40"
              disabled={disabled}
            >
              Generate my playlist
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}

