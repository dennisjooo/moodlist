'use client';

import { motion } from '@/components/ui/lazy-motion';
import { TrendingUp } from 'lucide-react';

export function AboutChallenges() {
    const challenges = [
        {
            title: "Session Management Hell",
            content: "Managing user sessions across multi-worker backends? Yeah, that's a whole different beast. What works locally doesn't always work in production, especially when you have multiple instances running."
        },
        {
            title: "AI Agents Are... Unpredictable",
            content: "The AI agentic approach sounded great in theory. In practice? Some recommendations are way off the mark. Even with iterative filtering and refinement, it's not always there yet. Turns out teaching an AI to understand musical taste is surprisingly difficult. I tried my best in making it clean and usable, but yeah, there will be edge cases I cannot fix. I also noticed that it's not that fast right now, trying to get it down to a minute max but it's a challenge."
        },
        {
            title: "AWS and That October 20th Outage",
            content: "I was in the middle of setting up AWS services when the big outage hit on 10/20/2025. Perfect timing, right? Nothing like debugging whether it's your code or the entire cloud infrastructure that's broken. Thanks Jeff, at least I'm still on the free tier. Eventually I ended up moving to Vercel for frontend (I know sorry, it's a touchy subject right now), Railway for backend, Neon for Postgres, and Upstash for Redis. What do you know, moving things there made a huge impact on speed and load times, especially to DB."
        },
        {
            title: "Cookies and CORS",
            content: "Those are huge pains in the ass for me. Since I'm deploying my frontend and backend on different domains, I had to somehow deal with both CORS and cookies issues. It ended up working sure, but a whole lot of debugging happened here and honestly it was quite a bit of a pain."
        },
        {
            title: "Spotify OAuth Deep Dive",
            content: "Implementing Spotify's OAuth flow was fascinating and frustrating in equal measure. Token refresh, scope management, redirect URIs—there's a lot to get right. Roughly at the end of development, I realised my scope for the Spotify API I'm using is only for development, meaning I can only add a limited number of people to the list. I understand the security measures Spotify has to make, but it pretty much limits the use case of the app."
        },
        {
            title: "Thinking of UX",
            content: "I'm not a UI/UX designer by any chance, so thinking about how things should work experience wise was something new to me. Of course, I have a certain way I expect the user to interact with the app, but there's NO guarantee that they will do so. It's a learning experience and I'm sure I'll get better at it with time."
        }
    ];

    return (
        <motion.section
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true, margin: '-100px' }}
            transition={{ duration: 0.4, ease: 'easeOut' }}
        >
            <div className="flex items-center gap-3 mb-6">
                <div className="p-2 rounded-lg bg-primary/10 border border-primary/10">
                    <TrendingUp className="w-4 h-4 text-primary" />
                </div>
                <h2 className="text-2xl font-semibold text-foreground">The Hard Parts</h2>
            </div>
            <div className="space-y-4 text-base leading-relaxed">
                <p className="text-muted-foreground">
                    Turns out, building a full-stack application from scratch is <em>hard</em>. Here are some things
                    that humbled me:
                </p>

                <div className="space-y-8 mt-6">
                    {challenges.map((challenge) => (
                        <div key={challenge.title} className="space-y-2">
                            <h3 className="text-lg font-medium text-foreground">{challenge.title}</h3>
                            <p className="text-muted-foreground">
                                {challenge.content}
                            </p>
                        </div>
                    ))}
                </div>
            </div>
        </motion.section>
    );
}
