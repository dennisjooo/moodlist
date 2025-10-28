'use client';

import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useMoodAnalysisStyling } from '@/lib/hooks';
import { Lightbulb, Music2, TrendingUp } from 'lucide-react';
import { useState } from 'react';
import { Button } from '@/components/ui/button';

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
  target_features?: {
    valence?: number;
    energy?: number;
    danceability?: number;
    acousticness?: number;
  };
}

interface MoodAnalysisCardProps {
  moodAnalysis: MoodAnalysis;
  metadata?: {
    iteration?: number;
    cohesion_score?: number;
  };
}

export default function MoodAnalysisCard({ moodAnalysis, metadata }: MoodAnalysisCardProps) {
  const colorScheme = moodAnalysis.color_scheme;
  const { primaryBadgeProps, secondaryBadgeProps, getKeywordBadgeProps } = useMoodAnalysisStyling(colorScheme);
  const [showTargets, setShowTargets] = useState(false);

  const renderTargetFeature = (label: string, value?: number) => {
    if (value === undefined || value === null) return null;
    return (
      <div className="flex items-center justify-between text-xs">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-medium text-foreground">{Math.round(value * 100)}%</span>
      </div>
    );
  };

  return (
    <Card className="group transition-all duration-300 hover:shadow-lg hover:shadow-black/10">
      <CardHeader className="space-y-2">
        <CardTitle className="text-lg flex items-center gap-2">
          <Lightbulb className="w-4 h-4 text-primary" />
          Mood Analysis & Strategy
        </CardTitle>
        {metadata?.cohesion_score && (
          <p className="text-xs text-muted-foreground">
            Cohesion score: <span className="font-medium text-foreground">{(metadata.cohesion_score * 100).toFixed(1)}%</span>
          </p>
        )}
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="space-y-3">
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

        {moodAnalysis.target_features && (
          <div className="rounded-lg border border-dashed border-muted-foreground/30 bg-muted/30 p-3 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-primary" />
                <span className="text-sm font-medium">Audio Target Profile</span>
              </div>
              <Button variant="ghost" size="sm" className="text-xs h-7" onClick={() => setShowTargets(prev => !prev)}>
                {showTargets ? 'Hide targets' : 'Show targets'}
              </Button>
            </div>
            {showTargets && (
              <div className="grid grid-cols-2 gap-2">
                {renderTargetFeature('Energy', moodAnalysis.target_features.energy)}
                {renderTargetFeature('Valence', moodAnalysis.target_features.valence)}
                {renderTargetFeature('Danceability', moodAnalysis.target_features.danceability)}
                {renderTargetFeature('Acousticness', moodAnalysis.target_features.acousticness)}
              </div>
            )}
          </div>
        )}

        <div className="rounded-lg bg-accent/60 border border-dashed border-primary/20 p-3">
          <div className="flex items-center gap-2 mb-2">
            <Music2 className="w-4 h-4 text-primary" />
            <span className="text-sm font-medium">How the playlist is built</span>
          </div>
          <p className="text-xs text-muted-foreground leading-relaxed">
            We start by understanding your mood and emotional targets, then discover anchor tracks and similar songs
            that match these energy and valence profiles. The quality gate ensures every track feels cohesive before
            the playlist is finalized.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}

