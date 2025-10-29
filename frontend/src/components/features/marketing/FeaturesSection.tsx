'use client';

import { motion } from '@/components/ui/lazy-motion';
import { useRef } from 'react';
import { HOW_IT_WORKS_STEPS } from '@/lib/constants/marketing';
import type { HowItWorksStep } from '@/lib/constants/marketing';

export function FeaturesSection() {
    const containerRef = useRef(null);

    const steps: HowItWorksStep[] = HOW_IT_WORKS_STEPS;

    return (
        <div ref={containerRef} className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 mt-16">
            <div className="flex flex-col items-center">
                <motion.div
                    className="mx-auto max-w-3xl text-center"
                    initial={{ opacity: 0, y: 24 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true, margin: '-80px' }}
                    transition={{ duration: 0.6, ease: 'easeOut' }}
                >
                    <span className="inline-flex items-center gap-2 rounded-full border border-primary/30 bg-primary/10 px-4 py-1 text-sm font-medium text-primary">
                        Simple process
                    </span>
                    <h2 className="mt-6 text-3xl font-semibold sm:text-4xl">
                        How It Works
                    </h2>
                    <p className="mt-3 text-base text-muted-foreground">
                        From mood prompt to perfect playlist in four simple steps
                    </p>
                </motion.div>

                <div className="relative w-full mt-16">
                    {/* Vertical line - mobile: left-aligned, desktop: centered */}
                    <div className="absolute left-6 lg:left-1/2 transform -translate-x-1/2 lg:-translate-x-1/2 w-1 bg-gradient-to-b from-blue-500 via-purple-600 via-pink-600 to-green-500 opacity-20 rounded-full h-full"
                    ></div>

                    <div className="space-y-16 lg:space-y-24">
                        {steps.map((step, index) => {
                            const IconComponent = step.icon;
                            const isLeft = index % 2 === 0;

                            return (
                                <div key={step.title} className="relative">
                                    {/* Timeline dot - mobile: left-aligned, desktop: centered */}
                                    <div className="absolute left-6 lg:left-1/2 transform -translate-x-1/2 lg:-translate-x-1/2 -translate-y-1/2 top-1/2 z-20">
                                        <motion.div
                                            className={`w-12 h-12 lg:w-16 lg:h-16 rounded-full bg-gradient-to-br ${step.color} flex items-center justify-center border-4 border-background`}
                                            style={{
                                                boxShadow: `0 0 0 4px rgba(0,0,0,0.1), 0 8px 32px rgba(0,0,0,0.12)`
                                            }}
                                            initial={{ opacity: 0, scale: 0.8 }}
                                            whileInView={{ opacity: 1, scale: 1 }}
                                            viewport={{ once: true, margin: "-50px" }}
                                            transition={{ duration: 0.6, delay: index * 0.1, ease: "easeOut" }}
                                        >
                                            <IconComponent className="w-6 h-6 lg:w-8 lg:h-8 text-white" />
                                        </motion.div>
                                    </div>

                                    {/* Mobile layout: simple left timeline + right content */}
                                    <div className="lg:hidden pl-16 ml-4 pr-8">
                                        <motion.div
                                            className="bg-white/5 dark:bg-black/20 backdrop-blur-sm rounded-xl p-6 border border-white/10"
                                            style={{
                                                boxShadow: `0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06)`
                                            }}
                                            initial={{ opacity: 0, x: 20 }}
                                            whileInView={{ opacity: 1, x: 0 }}
                                            viewport={{ once: true, margin: "-50px" }}
                                            transition={{ duration: 0.6, delay: index * 0.1, ease: "easeOut" }}
                                        >
                                            <h3 className="text-xl font-semibold mb-3">{step.title}</h3>
                                            <p className="text-muted-foreground leading-relaxed">
                                                {step.description}
                                            </p>
                                        </motion.div>
                                    </div>

                                    {/* Desktop layout: alternating sides with symmetric spacing */}
                                    <div className="hidden lg:grid lg:grid-cols-2 items-center min-h-[120px]">
                                        {/* Left side content - always has padding on the right to leave space for center icon */}
                                        <div className={`${isLeft ? 'order-1' : 'order-2 lg:order-1'} lg:pr-12`}>
                                            {isLeft && (
                                                <motion.div
                                                    className="bg-white/5 dark:bg-black/20 backdrop-blur-sm rounded-xl p-6 border border-white/10 lg:text-right"
                                                    style={{
                                                        boxShadow: `0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06)`
                                                    }}
                                                    initial={{ opacity: 0, x: -20 }}
                                                    whileInView={{ opacity: 1, x: 0 }}
                                                    viewport={{ once: true, margin: "-50px" }}
                                                    transition={{ duration: 0.6, delay: index * 0.1, ease: "easeOut" }}
                                                >
                                                    <h3 className="text-xl font-semibold mb-3">{step.title}</h3>
                                                    <p className="text-muted-foreground leading-relaxed">
                                                        {step.description}
                                                    </p>
                                                </motion.div>
                                            )}
                                        </div>

                                        {/* Right side content - always has padding on the left to leave space for center icon */}
                                        <div className={`${isLeft ? 'order-2' : 'order-1 lg:order-2'} lg:pl-12`}>
                                            {!isLeft && (
                                                <motion.div
                                                    className="bg-white/5 dark:bg-black/20 backdrop-blur-sm rounded-xl p-6 border border-white/10"
                                                    style={{
                                                        boxShadow: `0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06)`
                                                    }}
                                                    initial={{ opacity: 0, x: 20 }}
                                                    whileInView={{ opacity: 1, x: 0 }}
                                                    viewport={{ once: true, margin: "-50px" }}
                                                    transition={{ duration: 0.6, delay: index * 0.1, ease: "easeOut" }}
                                                >
                                                    <h3 className="text-xl font-semibold mb-3">{step.title}</h3>
                                                    <p className="text-muted-foreground leading-relaxed">
                                                        {step.description}
                                                    </p>
                                                </motion.div>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>
            </div>
        </div>
    );
}

