import Navigation from '@/components/Navigation';
import { WorkflowProgressSkeleton } from '@/components/shared/LoadingStates';
import { Button } from '@/components/ui/button';
import { DotPattern } from '@/components/ui/dot-pattern';
import { cn } from '@/lib/utils';
import { ArrowLeft } from 'lucide-react';

interface CreateSessionSkeletonProps {
    onBack: () => void;
}

export function CreateSessionSkeleton({ onBack }: CreateSessionSkeletonProps) {
    return (
        <div className="min-h-screen bg-background relative">
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

                <div className="flex items-center justify-center min-h-[60vh]">
                    <div className="w-full max-w-4xl">
                        <WorkflowProgressSkeleton />
                    </div>
                </div>
            </main>
        </div>
    );
}
