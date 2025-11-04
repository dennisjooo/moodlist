import { BackButton } from '@/components/shared';
import { CreateSessionLayout, createSessionCardClassName } from '@/components/features/create/CreateSessionLayout';
import type { Track } from '@/lib/types/workflow';
import dynamic from 'next/dynamic';

const PlaylistEditorComponent = dynamic(() => import('@/components/PlaylistEditor'), {
    loading: () => <div>Loading editor...</div>,
    ssr: false,
});

interface ColorScheme {
    primary: string;
    secondary: string;
    tertiary: string;
}

interface CreateSessionEditorProps {
    sessionId: string;
    recommendations: Track[];
    colorScheme?: ColorScheme;
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
        <CreateSessionLayout colorScheme={colorScheme}>
            <BackButton
                onClick={onBack}
                animated
                className="w-fit"
            />

            <div className={`${createSessionCardClassName} space-y-6 sm:space-y-8`}>
                <PlaylistEditorComponent
                    sessionId={sessionId}
                    recommendations={recommendations}
                    onSave={onSave}
                    onCancel={onCancel}
                />
            </div>
        </CreateSessionLayout>
    );
}
