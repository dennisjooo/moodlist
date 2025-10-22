import { AboutHero } from './AboutHero';
import { AboutInspiration } from './AboutInspiration';
import { AboutTechStack } from './AboutTechStack';
import { AboutChallenges } from './AboutChallenges';
import { AboutLessons } from './AboutLessons';
import { AboutConclusion } from './AboutConclusion';
import { AboutFooter } from './AboutFooter';

export function AboutLayout() {
    return (
        <div className="min-h-screen bg-background relative">
            <AboutHero />

            {/* Main Content */}
            <main className="relative z-10 max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 pt-16 sm:pt-24">
                {/* Blog Content */}
                <article className="space-y-16 sm:space-y-20">
                    <AboutInspiration />
                    <AboutTechStack />
                    <AboutChallenges />
                    <AboutLessons />
                    <AboutConclusion />
                </article>
            </main>

            <AboutFooter />
        </div>
    );
}
