import { Button } from '@/components/ui/button';
import { motion } from '@/components/ui/lazy-motion';
import { MOOD_TEMPLATES } from '@/lib/constants/moodTemplates';
import { Music } from 'lucide-react';
import Link from 'next/link';

export function EmptyState() {
    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
            className="text-center py-12"
        >
            <Music className="w-16 h-16 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-xl font-semibold mb-2">No playlists yet</h3>
            <p className="text-muted-foreground mb-8">
                Create your first AI-powered mood-based playlist! Try one of these prompts:
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 max-w-3xl mx-auto mb-8">
                {MOOD_TEMPLATES.slice(0, 6).map((template) => (
                    <Link
                        key={template.name}
                        href={`/create?mood=${encodeURIComponent(template.prompt)}`}
                        prefetch={false}
                    >
                        <Button
                            variant="outline"
                            className="w-full h-auto py-3 px-4 text-left justify-start hover:bg-accent transition-colors"
                        >
                            <span className="font-medium">
                                {template.name}
                            </span>
                        </Button>
                    </Link>
                ))}
            </div>
            <Link href="/create">
                <Button size="lg">✨ Create Custom Playlist</Button>
            </Link>
        </motion.div>
    );
}

