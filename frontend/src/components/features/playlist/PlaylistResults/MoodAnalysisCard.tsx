'use client';

import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useMoodAnalysisStyling } from '@/lib/hooks';

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
  const { primaryBadgeProps, secondaryBadgeProps, getKeywordBadgeProps } = useMoodAnalysisStyling(colorScheme);

  return (
    <Card className="group transition-all duration-300 hover:shadow-lg hover:shadow-black/10">
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
              className={primaryBadgeProps.className}
              style={primaryBadgeProps.style}
              onMouseEnter={primaryBadgeProps.onMouseEnter}
              onMouseLeave={primaryBadgeProps.onMouseLeave}
            >
              {moodAnalysis.primary_emotion}
            </Badge>
            <Badge
              variant="secondary"
              className={secondaryBadgeProps.className}
              style={secondaryBadgeProps.style}
              onMouseEnter={secondaryBadgeProps.onMouseEnter}
              onMouseLeave={secondaryBadgeProps.onMouseLeave}
            >
              {moodAnalysis.energy_level}
            </Badge>
            {moodAnalysis.search_keywords && moodAnalysis.search_keywords.slice(0, 6).map((keyword, idx) => {
              const keywordProps = getKeywordBadgeProps(keyword);
              return (
                <Badge
                  key={idx}
                  variant="outline"
                  className={keywordProps.className}
                  style={keywordProps.style}
                  onMouseEnter={keywordProps.onMouseEnter}
                  onMouseLeave={keywordProps.onMouseLeave}
                >
                  {keyword}
                </Badge>
              );
            })}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

