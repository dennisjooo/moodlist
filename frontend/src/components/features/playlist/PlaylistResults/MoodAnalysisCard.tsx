'use client';

import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface MoodAnalysis {
  mood_interpretation: string;
  primary_emotion: string;
  energy_level: string;
  search_keywords?: string[];
  color_scheme?: {
    primary: string;
    secondary: string;
    tertiary: string;
  };
}

interface MoodAnalysisCardProps {
  moodAnalysis: MoodAnalysis;
}

export default function MoodAnalysisCard({ moodAnalysis }: MoodAnalysisCardProps) {
  const colorScheme = moodAnalysis.color_scheme;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Mood Analysis</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <p className="text-sm leading-relaxed text-muted-foreground">
            {moodAnalysis.mood_interpretation}
          </p>

          <div className="flex flex-wrap gap-2">
            <Badge
              variant="secondary"
              className="capitalize"
              style={colorScheme ? {
                backgroundColor: `${colorScheme.primary}20`,
                color: colorScheme.primary,
                borderColor: colorScheme.primary
              } : undefined}
            >
              {moodAnalysis.primary_emotion}
            </Badge>
            <Badge
              variant="secondary"
              className="capitalize"
              style={colorScheme ? {
                backgroundColor: `${colorScheme.secondary}20`,
                color: colorScheme.secondary,
                borderColor: colorScheme.secondary
              } : undefined}
            >
              {moodAnalysis.energy_level}
            </Badge>
            {moodAnalysis.search_keywords && moodAnalysis.search_keywords.slice(0, 6).map((keyword, idx) => (
              <Badge
                key={idx}
                variant="outline"
                className="capitalize"
                style={colorScheme ? {
                  borderColor: colorScheme.tertiary,
                  color: colorScheme.tertiary
                } : undefined}
              >
                {keyword}
              </Badge>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

