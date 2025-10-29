'use client';

interface StatusMessageProps {
    status: string | null;
}

export function StatusMessage({ status }: StatusMessageProps) {
    const getMessage = (status: string | null) => {
        if (!status) return '🎵 Getting everything ready for you...';

        const statusMessages: Record<string, string> = {
            // Granular sub-steps
            gathering_seeds_fetching_top_tracks: '🎧 Exploring your favorite tracks...',
            gathering_seeds_fetching_top_artists: '🎤 Discovering your beloved artists...',
            gathering_seeds_analyzing_features: '🔊 Analyzing audio characteristics...',
            gathering_seeds_selecting_seeds: '🌱 Selecting the perfect seed tracks...',
            generating_recommendations_fetching: '🎼 Finding tracks that match your mood...',
            generating_recommendations_processing: '⚡ Ranking and filtering recommendations...',
            generating_recommendations_diversifying: '🎨 Adding variety to your playlist...',
            evaluating_quality_iteration: '🔍 Evaluating playlist quality...',
            optimizing_recommendations_iteration: '✨ Refining and perfecting your playlist...',
            // Main workflow statuses
            analyzing_mood: '🤔 Analyzing your mood and finding the perfect vibe...',
            gathering_seeds: '🎵 Diving into your music library...',
            generating_recommendations: '🎼 Curating your perfect music selection...',
            evaluating_quality: '🔍 Making sure every track fits your mood perfectly...',
            optimizing_recommendations: '✨ Perfecting the playlist sequence...',
            ordering_playlist: '🎢 Creating the perfect energy flow...',
            awaiting_user_input: '✏️ Ready for your creative touch!',
            processing_edits: '🔄 Applying your changes with care...',
            creating_playlist: '🎵 Saving your personalized playlist to Spotify...',
            completed: '🎉 Your perfect playlist is ready to play!',
            failed: '❌ Oops, something went wrong',
        };

        // Check for exact match first
        if (statusMessages[status]) {
            return statusMessages[status];
        }

        // Check for partial matches (sub-steps)
        for (const [key, message] of Object.entries(statusMessages)) {
            if (status.includes(key)) {
                return message;
            }
        }

        return '🎵 Getting everything ready for you...';
    };

    return (
        <div className="text-sm font-medium flex-1">
            {getMessage(status)}
        </div>
    );
}

