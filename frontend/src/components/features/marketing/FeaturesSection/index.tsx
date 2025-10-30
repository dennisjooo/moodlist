'use client';

import { HOW_IT_WORKS_STEPS } from '@/lib/constants/marketing';
import { SectionHeader } from './SectionHeader';
import { ConnectionLines } from './ConnectionLines';
import { StepCard } from './StepCard';

export function FeaturesSection() {
  return (
    <section className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24 lg:py-32">
      {/* Ambient Background Blurs */}
      <div aria-hidden="true" className="absolute inset-0 -z-10 pointer-events-none">
        <div className="absolute top-20 left-1/4 w-96 h-96 bg-primary/5 rounded-full blur-3xl" />
        <div className="absolute bottom-20 right-1/4 w-96 h-96 bg-purple-500/5 rounded-full blur-3xl" />
      </div>

      <SectionHeader />

      {/* Steps Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 lg:gap-8 relative md:px-6 lg:px-8">
        <ConnectionLines />

        {HOW_IT_WORKS_STEPS.map((step, index) => (
          <StepCard
            key={step.title}
            step={step}
            index={index}
            isLastStep={index === HOW_IT_WORKS_STEPS.length - 1}
          />
        ))}
      </div>
    </section>
  );
}

