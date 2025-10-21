'use client';

import { CheckCircle, Loader2, Music, XCircle } from 'lucide-react';

interface StatusIconProps {
    status: string | null;
}

export function StatusIcon({ status }: StatusIconProps) {
    switch (status) {
        case 'analyzing_mood':
        case 'gathering_seeds':
        case 'generating_recommendations':
        case 'evaluating_quality':
        case 'optimizing_recommendations':
        case 'processing_edits':
        case 'creating_playlist':
            return <Loader2 className="w-4 h-4 animate-spin" />;
        case 'completed':
            return <CheckCircle className="w-4 h-4 text-green-500" />;
        case 'failed':
            return <XCircle className="w-4 h-4 text-red-500" />;
        case 'awaiting_user_input':
            return <Music className="w-4 h-4" />;
        default:
            return <Music className="w-4 h-4" />;
    }
}

