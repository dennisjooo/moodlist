import { Lightbulb } from 'lucide-react';

export function AboutInspiration() {
    return (
        <section>
            <div className="flex items-center gap-3 mb-6">
                <div className="p-2 rounded-lg bg-primary/10 border border-primary/10">
                    <Lightbulb className="w-4 h-4 text-primary" />
                </div>
                <h2 className="text-2xl font-semibold text-foreground">The Inspiration</h2>
            </div>
            <div className="space-y-4 text-base leading-relaxed">
                <p className="text-muted-foreground">
                    Remember that Spotify feature that could create a playlist from another playlist? I used to rely on it
                    heavily for music discovery—finding interesting songs to add to my own collections.
                </p>
                <p className="text-muted-foreground">
                    The idea for MoodList is simple: <strong className="text-foreground">just describe what you want,
                        and get a solid playlist out of it.</strong> No manual searching, no endless scrolling. Just a query
                    and boom—curated music that&apos;s listenable by you on Spotify.
                </p>
            </div>
        </section>
    );
}
