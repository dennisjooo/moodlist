import { Button } from '@/components/ui/button';
import MoodBackground from '@/components/shared/MoodBackground';
import { DotPattern } from '@/components/ui/dot-pattern';
import Navigation from '@/components/Navigation';
import PlaylistEditor from '@/components/PlaylistEditor';
import { ArrowLeft } from 'lucide-react';
import { cn } from '@/lib/utils';
import dynamic from 'next/dynamic';

const PlaylistEditorComponent = dynamic(() => import('@/components/PlaylistEditor'), {
    loading: () => <div>Loading editor...</div>,
    ssr: false,
});

interface CreateSessionEditorProps {
    sessionId: string;
    recommendations: any[];
    colorScheme?: any;
    onBack: () => void;
    onSave: () => void;
    onCancel: () => void;
}

export function CreateSessionEditor({
    sessionId,
    recommendations,
    colorScheme,
    onBack,
    onSave,
    onCancel,
}: CreateSessionEditorProps) {
    return (
        <div className="min-h-screen bg-background relative">
            <MoodBackground
                colorScheme={colorScheme}
                style="linear-diagonal"
                opacity={0.2}
            />

            <div className="fixed inset-0 z-0 opacity-0 animate-[fadeInDelayed_1.2s_ease-in-out_forwards]">
                <DotPattern
                    className={cn(
                        "[mask-image:radial-gradient(400px_circle_at_center,white,transparent)]",
                    )}
                />
            </div>

            <Navigation />

            <main className="relative z-10 max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
                {/* Back Button */}
                <Button
                    variant="ghost"
                    onClick={onBack}
                    className="mb-6 gap-2"
                >
                    <ArrowLeft className="w-4 h-4" />
                    Back
                </Button>

                <PlaylistEditorComponent
                    sessionId={sessionId}
                    recommendations={recommendations}
                    onSave={onSave}
                    onCancel={onCancel}
                />
            </main>
        </div>
    );
}
