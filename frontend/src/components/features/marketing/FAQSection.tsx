'use client';

import { motion } from '@/components/ui/lazy-motion';
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion';
import { FeatureBadge } from '@/components/ui/feature-badge';
import { useId } from 'react';
import { FAQ_ITEMS } from '@/lib/constants/marketing';
import { HelpCircle } from 'lucide-react';

export default function FAQSection() {
  const baseId = useId();

  return (
    <section className="relative mt-16 px-4 sm:px-6 lg:px-8">
      <div className="relative mx-auto max-w-4xl py-16 sm:py-20">
        <motion.div
          className="mb-12 text-center sm:mb-16"
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-80px' }}
          transition={{ duration: 0.6, ease: 'easeOut' }}
        >
          <FeatureBadge icon={HelpCircle}>
            Quick answers
          </FeatureBadge>
          <h2 className="mt-6 text-3xl font-semibold sm:text-4xl">
            Got questions?
          </h2>
          <p className="mx-auto mt-3 max-w-2xl text-base text-muted-foreground">
            Here&apos;s what you probably want to know before diving in.
          </p>
        </motion.div>

        <Accordion type="single" collapsible className="space-y-4">
          {FAQ_ITEMS.map((item, index) => {
            const value = `${baseId}-${index}`;
            return (
              <motion.div
                key={value}
                initial={{ opacity: 0, y: 16 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: '-50px' }}
                transition={{ duration: 0.5, delay: index * 0.08, ease: 'easeOut' }}
              >
                <AccordionItem
                  value={value}
                  className="overflow-hidden rounded-xl border border-white/10 bg-white/5 backdrop-blur-sm dark:bg-black/20"
                  style={{
                    boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06)',
                  }}
                >
                  <AccordionTrigger className="px-5 py-5 text-left text-base font-semibold hover:no-underline sm:px-6 sm:text-lg">
                    {item.question}
                  </AccordionTrigger>
                  <AccordionContent className="px-5 pb-5 text-sm leading-relaxed text-muted-foreground sm:px-6 sm:text-base">
                    {item.answer}
                  </AccordionContent>
                </AccordionItem>
              </motion.div>
            );
          })}
        </Accordion>
      </div>
    </section>
  );
}
