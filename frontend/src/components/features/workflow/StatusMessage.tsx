'use client';

interface StatusMessageProps {
    status: string | null;
}

export function StatusMessage({ status }: StatusMessageProps) {
    const getMessage = (status: string | null) => {
        switch (status) {
            case 'analyzing_mood':
                return '🤔 Analyzing your mood and finding the perfect vibe...';
            case 'gathering_seeds':
                return '🎵 Diving into your music library to understand your taste...';
            case 'generating_recommendations':
                return '🎼 Curating your perfect music selection...';
            case 'evaluating_quality':
                return '🔍 Making sure every track fits your mood perfectly...';
            case 'optimizing_recommendations':
                return '✨ Perfecting the playlist sequence...';
            case 'awaiting_user_input':
                return '✏️ Ready for your creative touch!';
            case 'processing_edits':
                return '🔄 Applying your changes with care...';
            case 'creating_playlist':
                return '🎵 Saving your personalized playlist to Spotify...';
            case 'completed':
                return '🎉 Your perfect playlist is ready to play!';
            case 'failed':
                return '❌ Oops, something went wrong';
            default:
                return '🎵 Getting everything ready for you...';
        }
    };

    return (
        <div className="text-sm font-medium flex-1">
            {getMessage(status)}
        </div>
    );
}

