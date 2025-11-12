'use client';

import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';
import { Badge } from '@/components/ui/badge';
import { motion } from '@/components/ui/lazy-motion';
import { Wrench, Monitor, Server, Globe, Code, Database, Activity, Settings, Palette, Sparkles, Zap, Shield, Key } from 'lucide-react';

export function AboutTechStack() {
    return (
        <motion.section
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true, margin: '-100px' }}
            transition={{ duration: 0.4, ease: 'easeOut' }}
        >
            <div className="flex items-center gap-3 mb-6">
                <div className="p-2 rounded-lg bg-primary/10 border border-primary/10">
                    <Wrench className="w-4 h-4 text-primary" />
                </div>
                <h2 className="text-2xl font-semibold text-foreground">What I Built With</h2>
            </div>
            <div className="space-y-8 text-base leading-relaxed">
                <p className="text-muted-foreground">
                    This project uses both <strong className="text-foreground">Reccobeat</strong> and{' '}
                    <strong className="text-foreground">Spotify APIs</strong>—huge kudos and thanks to them
                    for their wonderful APIs that made this possible. I used this as a learning playground to dive deep into modern web development.
                </p>

                {/* Tech Stack Accordions */}
                <div>
                    <Accordion type="single" collapsible className="w-full">
                        {/* Frontend Accordion */}
                        <AccordionItem value="frontend">
                            <AccordionTrigger className="hover:no-underline">
                                <div className="flex items-center gap-3">
                                    <div className="p-2 rounded-lg bg-blue-500/10 border border-blue-500/20">
                                        <Monitor className="w-4 h-4 text-blue-500" />
                                    </div>
                                    <span className="text-lg font-medium text-foreground">Frontend</span>
                                    <Badge variant="secondary" className="text-xs">13 technologies</Badge>
                                </div>
                            </AccordionTrigger>
                            <AccordionContent className="space-y-4">
                                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                    <TechCard
                                        icon={<Code className="w-4 h-4 text-blue-600 dark:text-blue-400" />}
                                        name="Next.js 16"
                                        description="App Router & React 19 for modern SSR experiences"
                                        bgColor="blue"
                                    />
                                    <TechCard
                                        icon={<Settings className="w-4 h-4 text-blue-600 dark:text-blue-400" />}
                                        name="TypeScript"
                                        description="Type safety and enhanced developer experience"
                                        bgColor="blue"
                                    />
                                    <TechCard
                                        icon={<Palette className="w-4 h-4 text-blue-600 dark:text-blue-400" />}
                                        name="Tailwind CSS"
                                        description="Utility-first styling with custom design system"
                                        bgColor="blue"
                                    />
                                    <TechCard
                                        icon={<Sparkles className="w-4 h-4 text-blue-600 dark:text-blue-400" />}
                                        name="Shadcn/ui"
                                        description="Component library built on Radix UI primitives"
                                        bgColor="blue"
                                    />
                                    <TechCard
                                        icon={<Zap className="w-4 h-4 text-blue-600 dark:text-blue-400" />}
                                        name="Magic UI"
                                        description="Enhanced animations and interactive components"
                                        bgColor="blue"
                                    />
                                    <TechCard
                                        icon={<Activity className="w-4 h-4 text-blue-600 dark:text-blue-400" />}
                                        name="Lucide React"
                                        description="Consistent, beautiful icons throughout the app"
                                        bgColor="blue"
                                    />
                                    <TechCard
                                        icon={<Zap className="w-4 h-4 text-blue-600 dark:text-blue-400" />}
                                        name="Framer Motion"
                                        description="Smooth animations and gesture interactions"
                                        bgColor="blue"
                                    />
                                    <TechCard
                                        icon={<Sparkles className="w-4 h-4 text-blue-600 dark:text-blue-400" />}
                                        name="@dnd-kit"
                                        description="Modern drag-and-drop functionality"
                                        bgColor="blue"
                                    />
                                    <TechCard
                                        icon={<Activity className="w-4 h-4 text-blue-600 dark:text-blue-400" />}
                                        name="TanStack Virtual"
                                        description="Efficiently render large lists with virtualization"
                                        bgColor="blue"
                                    />
                                    <TechCard
                                        icon={<Palette className="w-4 h-4 text-blue-600 dark:text-blue-400" />}
                                        name="next-themes"
                                        description="Seamless dark/light theme switching"
                                        bgColor="blue"
                                    />
                                    <TechCard
                                        icon={<Zap className="w-4 h-4 text-blue-600 dark:text-blue-400" />}
                                        name="Sonner"
                                        description="Elegant toast notifications"
                                        bgColor="blue"
                                    />
                                    <TechCard
                                        icon={<Activity className="w-4 h-4 text-blue-600 dark:text-blue-400" />}
                                        name="Axios"
                                        description="Promise-based HTTP client for API requests"
                                        bgColor="blue"
                                    />
                                    <TechCard
                                        icon={<Settings className="w-4 h-4 text-blue-600 dark:text-blue-400" />}
                                        name="Zustand"
                                        description="Lightweight state management with minimal boilerplate"
                                        bgColor="blue"
                                    />
                                </div>
                            </AccordionContent>
                        </AccordionItem>

                        {/* Backend Accordion */}
                        <AccordionItem value="backend">
                            <AccordionTrigger className="hover:no-underline">
                                <div className="flex items-center gap-3">
                                    <div className="p-2 rounded-lg bg-green-500/10 border border-green-500/20">
                                        <Server className="w-4 h-4 text-green-500" />
                                    </div>
                                    <span className="text-lg font-medium text-foreground">Backend</span>
                                    <Badge variant="secondary" className="text-xs">11 technologies</Badge>
                                </div>
                            </AccordionTrigger>
                            <AccordionContent className="space-y-4">
                                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                    <TechCard
                                        icon={<Zap className="w-4 h-4 text-green-600 dark:text-green-400" />}
                                        name="FastAPI"
                                        description="Async Python for high-performance REST APIs"
                                        bgColor="green"
                                    />
                                    <TechCard
                                        icon={<Database className="w-4 h-4 text-green-600 dark:text-green-400" />}
                                        name="PostgreSQL"
                                        description="SQLAlchemy ORM for reliable data persistence"
                                        bgColor="green"
                                    />
                                    <TechCard
                                        icon={<Activity className="w-4 h-4 text-green-600 dark:text-green-400" />}
                                        name="Redis"
                                        description="Caching and rate limiting for external API calls"
                                        bgColor="green"
                                    />
                                    <TechCard
                                        icon={<Sparkles className="w-4 h-4 text-green-600 dark:text-green-400" />}
                                        name="LangGraph"
                                        description="Building sophisticated AI agents with LangChain"
                                        bgColor="green"
                                    />
                                    <TechCard
                                        icon={<Shield className="w-4 h-4 text-green-600 dark:text-green-400" />}
                                        name="JWT Auth"
                                        description="Encrypted token storage and session management"
                                        bgColor="green"
                                    />
                                    <TechCard
                                        icon={<Key className="w-4 h-4 text-green-600 dark:text-green-400" />}
                                        name="Spotify OAuth"
                                        description="Token refresh and scope management integration"
                                        bgColor="green"
                                    />
                                    <TechCard
                                        icon={<Activity className="w-4 h-4 text-green-600 dark:text-green-400" />}
                                        name="Structlog"
                                        description="Comprehensive request/response logging to database"
                                        bgColor="green"
                                    />
                                    <TechCard
                                        icon={<Settings className="w-4 h-4 text-green-600 dark:text-green-400" />}
                                        name="Pydantic"
                                        description="Robust data validation and serialization"
                                        bgColor="green"
                                    />
                                    <TechCard
                                        icon={<Zap className="w-4 h-4 text-green-600 dark:text-green-400" />}
                                        name="Uvicorn"
                                        description="ASGI server for high-performance async deployment"
                                        bgColor="green"
                                    />
                                    <TechCard
                                        icon={<Activity className="w-4 h-4 text-green-600 dark:text-green-400" />}
                                        name="httpx"
                                        description="Modern async HTTP client for external APIs"
                                        bgColor="green"
                                    />
                                    <TechCard
                                        icon={<Shield className="w-4 h-4 text-green-600 dark:text-green-400" />}
                                        name="SlowAPI"
                                        description="Rate limiting to manage API usage efficiently"
                                        bgColor="green"
                                    />
                                    <TechCard
                                        icon={<Activity className="w-4 h-4 text-green-600 dark:text-green-400" />}
                                        name="Tenacity"
                                        description="Retry logic and circuit breaker patterns"
                                        bgColor="green"
                                    />
                                </div>
                            </AccordionContent>
                        </AccordionItem>

                        {/* External Services Accordion */}
                        <AccordionItem value="external">
                            <AccordionTrigger className="hover:no-underline">
                                <div className="flex items-center gap-3">
                                    <div className="p-2 rounded-lg bg-purple-500/10 border border-purple-500/20">
                                        <Globe className="w-4 h-4 text-purple-500" />
                                    </div>
                                    <span className="text-lg font-medium text-foreground">External Services</span>
                                    <Badge variant="secondary" className="text-xs">7 services</Badge>
                                </div>
                            </AccordionTrigger>
                            <AccordionContent className="space-y-4">
                                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                    <TechCard
                                        icon={<Monitor className="w-4 h-4 text-purple-600 dark:text-purple-400" />}
                                        name="Spotify Web API"
                                        description="Music data and playlist management"
                                        bgColor="purple"
                                    />
                                    <TechCard
                                        icon={<Sparkles className="w-4 h-4 text-purple-600 dark:text-purple-400" />}
                                        name="ReccoBeat API"
                                        description="Advanced music recommendations and audio features"
                                        bgColor="purple"
                                    />
                                    <TechCard
                                        icon={<Zap className="w-4 h-4 text-purple-600 dark:text-purple-400" />}
                                        name="OpenRouter"
                                        description="LLM inference and generation services"
                                        bgColor="purple"
                                    />
                                    <TechCard
                                        icon={<Server className="w-4 h-4 text-purple-600 dark:text-purple-400" />}
                                        name="Railway"
                                        description="Cloud platform for backend deployment and hosting"
                                        bgColor="purple"
                                    />
                                    <TechCard
                                        icon={<Zap className="w-4 h-4 text-purple-600 dark:text-purple-400" />}
                                        name="Vercel"
                                        description="Frontend deployment and edge network infrastructure"
                                        bgColor="purple"
                                    />
                                    <TechCard
                                        icon={<Activity className="w-4 h-4 text-purple-600 dark:text-purple-400" />}
                                        name="Upstash"
                                        description="Serverless Redis for caching and rate limiting"
                                        bgColor="purple"
                                    />
                                    <TechCard
                                        icon={<Database className="w-4 h-4 text-purple-600 dark:text-purple-400" />}
                                        name="Neon"
                                        description="Serverless PostgreSQL database hosting"
                                        bgColor="purple"
                                    />
                                </div>
                            </AccordionContent>
                        </AccordionItem>
                    </Accordion>
                </div>
            </div>
        </motion.section>
    );
}

interface TechCardProps {
    icon: React.ReactNode;
    name: string;
    description: string;
    bgColor: 'blue' | 'green' | 'purple';
}

function TechCard({ icon, name, description, bgColor }: TechCardProps) {
    const bgClasses = {
        blue: "bg-gradient-to-br from-blue-50/50 to-blue-100/30 dark:from-blue-950/20 dark:to-blue-900/10 border-blue-200/50 dark:border-blue-800/30",
        green: "bg-gradient-to-br from-green-50/50 to-green-100/30 dark:from-green-950/20 dark:to-green-900/10 border-green-200/50 dark:border-green-800/30",
        purple: "bg-gradient-to-br from-purple-50/50 to-purple-100/30 dark:from-purple-950/20 dark:to-purple-900/10 border-purple-200/50 dark:border-purple-800/30"
    };

    return (
        <div className={`flex items-start gap-3 p-4 rounded-lg ${bgClasses[bgColor]} border`}>
            <div className={`p-2 rounded-lg bg-${bgColor}-500/10 flex-shrink-0`}>
                {icon}
            </div>
            <div className="min-w-0 flex-1">
                <h4 className="text-sm font-semibold text-foreground mb-1">{name}</h4>
                <p className="text-xs text-muted-foreground">{description}</p>
            </div>
        </div>
    );
}
