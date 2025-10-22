import { TrendingUp } from 'lucide-react';

export function AboutChallenges() {
    return (
        <section>
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
                    <div className="space-y-2">
                        <h3 className="text-lg font-medium text-foreground">Session Management Hell</h3>
                        <p className="text-muted-foreground">
                            Managing user sessions across multi-worker backends? Yeah, that&apos;s a whole different beast.
                            What works locally doesn&apos;t always work in production, especially when you have multiple
                            instances running.
                        </p>
                    </div>

                    <div className="space-y-2">
                        <h3 className="text-lg font-medium text-foreground">AWS and That October 20th Outage</h3>
                        <p className="text-muted-foreground">
                            I was in the middle of setting up AWS services when the big outage hit on 10/20/2025.
                            Perfect timing, right? Nothing like debugging whether it&apos;s your code or the entire
                            cloud infrastructure that&apos;s broken. Thanks Jeff, at least I&apos;m still on the free tier.
                        </p>
                    </div>

                    <div className="space-y-2">
                        <h3 className="text-lg font-medium text-foreground">AI Agents Are... Unpredictable</h3>
                        <p className="text-muted-foreground">
                            The AI agentic approach sounded great in theory. In practice? Some recommendations are way off
                            the mark. Even with iterative filtering and refinement, it&apos;s not always there yet. Turns out
                            teaching an AI to understand musical taste is surprisingly difficult.
                        </p>
                    </div>

                    <div className="space-y-2">
                        <h3 className="text-lg font-medium text-foreground">Spotify OAuth Deep Dive</h3>
                        <p className="text-muted-foreground">
                            Implementing Spotify&apos;s OAuth flow was fascinating and frustrating in equal measure.
                            Token refresh, scope management, redirect URIs—there&apos;s a lot to get right.
                        </p>
                    </div>
                </div>
            </div>
        </section>
    );
}
