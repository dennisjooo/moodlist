'use client';

import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useMoodAnalysisStyling } from '@/lib/hooks';
import { ChevronDown } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';

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
  totalLLMCost?: number;
  totalPromptTokens?: number;
  totalCompletionTokens?: number;
  totalTokens?: number;
}

export default function MoodAnalysisCard({
  moodAnalysis,
  totalLLMCost,
  totalPromptTokens,
  totalCompletionTokens,
  totalTokens
}: MoodAnalysisCardProps) {
  const colorScheme = moodAnalysis.color_scheme;
  const { primaryBadgeProps, secondaryBadgeProps, getKeywordBadgeProps } = useMoodAnalysisStyling(colorScheme);
  const [isMetricsOpen, setIsMetricsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const hasMetrics = (totalLLMCost !== undefined && totalLLMCost > 0) || (totalTokens !== undefined && totalTokens > 0);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsMetricsOpen(false);
      }
    };

    if (isMetricsOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [isMetricsOpen]);

  return (
    <Card className="group transition-all duration-300 hover:shadow-lg hover:shadow-black/10">
      <CardHeader>
        <div className="flex items-center justify-between gap-4">
          <CardTitle className="text-lg">Mood Analysis</CardTitle>
          {hasMetrics && (
            <div className="relative" ref={dropdownRef}>
              <button
                onClick={() => setIsMetricsOpen(!isMetricsOpen)}
                className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs font-mono text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors"
                aria-expanded={isMetricsOpen}
                aria-label="View LLM metrics"
              >
                {totalLLMCost !== undefined && totalLLMCost > 0 && (
                  <span className="font-semibold">${totalLLMCost.toFixed(4)}</span>
                )}
                <ChevronDown
                  className={`h-3 w-3 transition-transform duration-200 ${isMetricsOpen ? 'rotate-180' : ''}`}
                />
              </button>

              {isMetricsOpen && (
                <div className="absolute right-0 top-full mt-1 z-10 min-w-[200px] rounded-md border bg-popover p-3 shadow-md animate-in fade-in-0 zoom-in-95 slide-in-from-top-2 duration-200">
                  <div className="space-y-2 text-xs font-mono">
                    {totalLLMCost !== undefined && totalLLMCost > 0 && (
                      <div className="flex justify-between items-center gap-4">
                        <span className="text-muted-foreground">Cost</span>
                        <span className="font-semibold">${totalLLMCost.toFixed(4)}</span>
                      </div>
                    )}
                    {totalTokens !== undefined && totalTokens > 0 && (
                      <div className="flex justify-between items-center gap-4">
                        <span className="text-muted-foreground">Total Tokens</span>
                        <span className="font-semibold">{totalTokens.toLocaleString()}</span>
                      </div>
                    )}
                    {totalPromptTokens !== undefined && totalPromptTokens > 0 && (
                      <div className="flex justify-between items-center gap-4">
                        <span className="text-muted-foreground">Input</span>
                        <span className="font-semibold">{totalPromptTokens.toLocaleString()}</span>
                      </div>
                    )}
                    {totalCompletionTokens !== undefined && totalCompletionTokens > 0 && (
                      <div className="flex justify-between items-center gap-4">
                        <span className="text-muted-foreground">Output</span>
                        <span className="font-semibold">{totalCompletionTokens.toLocaleString()}</span>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
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
              const keywordProps = getKeywordBadgeProps();
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

