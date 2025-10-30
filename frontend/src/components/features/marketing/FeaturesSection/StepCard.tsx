'use client';

import { motion } from '@/components/ui/lazy-motion';
import { ArrowRight } from 'lucide-react';
import type { HowItWorksStep } from '@/lib/constants/marketing';

interface StepCardProps {
  step: HowItWorksStep;
  index: number;
  isLastStep: boolean;
}

export function StepCard({ step, index, isLastStep }: StepCardProps) {
  const IconComponent = step.icon;

  return (
    <motion.div
      className="relative group px-1"
      initial={{ opacity: 0, y: 30 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-50px' }}
      transition={{ duration: 0.6, delay: index * 0.15, ease: [0.25, 0.4, 0.25, 1] }}
    >
      <div className="relative h-full">
        {/* Hover Glow Effect */}
        <div
          aria-hidden="true"
          className={`absolute -inset-2 rounded-[28px] bg-gradient-to-br ${step.color} opacity-0 blur-3xl transition-all duration-700 group-hover:opacity-20 group-hover:blur-[48px]`}
        />

        {/* Card */}
        <div className="relative h-full overflow-hidden rounded-3xl border border-border/40 bg-gradient-to-b from-background/95 to-background/80 backdrop-blur-xl shadow-[0_8px_32px_-12px_rgba(0,0,0,0.12)] dark:shadow-[0_8px_32px_-12px_rgba(0,0,0,0.4)] transition-all duration-500 group-hover:-translate-y-1 group-hover:border-border/60 group-hover:shadow-[0_20px_48px_-12px_rgba(0,0,0,0.18)] dark:group-hover:shadow-[0_20px_48px_-12px_rgba(0,0,0,0.6)]">
          {/* Top Border Accent */}
          <div className={`absolute top-0 left-0 right-0 h-px bg-gradient-to-r ${step.color} opacity-0 group-hover:opacity-60 transition-opacity duration-500`} />

          <div className="p-8 lg:p-10 flex flex-col h-full relative">
            {/* Decorative Corner Blur */}
            <div aria-hidden="true" className="absolute top-6 right-6 lg:top-8 lg:right-8">
              <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${step.color} opacity-[0.07] blur-xl`} />
            </div>

            {/* Icon & Step Number */}
            <div className="flex items-start justify-between mb-6 relative z-10">
              <div className="relative">
                {/* Pulsing Glow */}
                <motion.div
                  aria-hidden="true"
                  className={`absolute inset-0 rounded-2xl bg-gradient-to-br ${step.color} opacity-20 blur-xl`}
                  animate={{
                    opacity: [0.2, 0.3, 0.2],
                    scale: [1, 1.05, 1],
                  }}
                  transition={{
                    duration: 3,
                    repeat: Infinity,
                    ease: "easeInOut",
                  }}
                />
                {/* Icon */}
                <div className={`relative w-14 h-14 lg:w-16 lg:h-16 rounded-2xl bg-gradient-to-br ${step.color} flex items-center justify-center shadow-lg transition-all duration-300 group-hover:scale-110 group-hover:rotate-3`}>
                  <IconComponent className="w-7 h-7 lg:w-8 lg:h-8 text-white" />
                </div>
              </div>

              {/* Large Step Number */}
              <motion.span
                className="text-6xl lg:text-7xl font-bold bg-gradient-to-br from-muted-foreground/10 to-muted-foreground/5 bg-clip-text text-transparent select-none"
                initial={{ opacity: 0, x: 20 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: index * 0.15 + 0.2 }}
              >
                {index + 1}
              </motion.span>
            </div>

            {/* Content */}
            <div className="flex-1 relative z-10">
              <h3 className="text-xl lg:text-2xl font-semibold tracking-tight mb-3 group-hover:text-foreground transition-colors duration-300">
                {step.title}
              </h3>
              <p className="text-muted-foreground leading-relaxed text-sm lg:text-base">
                {step.description}
              </p>
            </div>

            {/* Bottom Accent Bar */}
            <motion.div
              className={`mt-6 h-1 rounded-full bg-gradient-to-r ${step.color} opacity-0 group-hover:opacity-100`}
              initial={{ scaleX: 0 }}
              whileInView={{ scaleX: 0 }}
              whileHover={{ scaleX: 1 }}
              transition={{ duration: 0.4 }}
            />

            {/* Mobile Arrow Indicator */}
            {!isLastStep && (
              <motion.div
                className="md:hidden flex justify-center mt-8 -mb-4"
                initial={{ opacity: 0, y: -10 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.4, delay: index * 0.15 + 0.4 }}
              >
                <div className={`w-10 h-10 rounded-full bg-gradient-to-br ${step.color} flex items-center justify-center opacity-70 shadow-lg`}>
                  <ArrowRight className="w-5 h-5 text-white rotate-90" />
                </div>
              </motion.div>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  );
}

