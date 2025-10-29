'use client';

import { motion } from '@/components/ui/lazy-motion';
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion';
import { useId } from 'react';
import { FAQ_ITEMS } from '@/lib/constants/marketing';

export default function FAQSection() {
  const baseId = useId();

  return (
    <section className="relative mt-16 border-y border-border/50 bg-gradient-to-b from-background via-background/90 to-background">
      <div className="absolute inset-x-0 -top-10 flex justify-center blur-3xl opacity-40">
        <div className="h-24 w-2/3 max-w-2xl bg-gradient-to-r from-primary/30 via-primary/10 to-transparent" />
      </div>
      <div className="relative mx-auto max-w-5xl px-4 py-20 sm:px-6 lg:px-8">
        <motion.div
          className="text-center"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-50px' }}
          transition={{ duration: 0.6, ease: 'easeOut' }}
        >
          <p className="mb-4 text-sm font-semibold tracking-wide text-primary">FAQ</p>
          <h2 className="text-3xl font-bold sm:text-4xl">Get quick answers</h2>
          <p className="mt-3 text-muted-foreground">
            New to Moodlist? These common questions will guide you from your first prompt to your first playlist.
          </p>
        </motion.div>

        <div className="mt-10">
          <Accordion type="single" collapsible className="space-y-4">
            {FAQ_ITEMS.map((item, index) => {
              const value = `${baseId}-${index}`;
              return (
                <motion.div
                  key={value}
                  initial={{ opacity: 0, y: 16 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true, margin: '-50px' }}
                  transition={{ duration: 0.4, delay: index * 0.05, ease: 'easeOut' }}
                >
                  <AccordionItem
                    value={value}
                    className="overflow-hidden rounded-2xl border border-border/60 bg-background/80 shadow-[0_20px_45px_-30px_rgba(59,130,246,0.45)]"
                  >
                    <AccordionTrigger className="px-6 py-5 text-base font-medium sm:text-lg">
                      {item.question}
                    </AccordionTrigger>
                    <AccordionContent className="px-6 pb-6 text-sm leading-relaxed text-muted-foreground sm:text-base">
                      {item.answer}
                    </AccordionContent>
                  </AccordionItem>
                </motion.div>
              );
            })}
          </Accordion>
        </div>
      </div>
    </section>
  );
}
