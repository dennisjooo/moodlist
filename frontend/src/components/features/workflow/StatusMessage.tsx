'use client';

interface StatusMessageProps {
    status: string | null;
    currentStep?: string | null;
}

export function StatusMessage({ status, currentStep }: StatusMessageProps) {
    const getMessage = (status: string | null, currentStep?: string | null) => {
        // Prioritize currentStep if available (it's more specific)
        const statusToCheck = currentStep || status;

        if (!statusToCheck) return '🎵 Preparing something magical for you...';

        const statusMessages: Record<string, string> = {
            // Initialization
            initializing: '🚀 Warming up the music engines...',
            pending: '⏳ Gathering our musical wits...',

            // Intent and mood analysis
            analyzing_intent: '🔎 Reading between the musical lines...',
            analyzing_mood: '🤔 Decoding your vibe like a musical detective...',

            // Granular sub-steps for gathering_seeds
            gathering_seeds_searching_user_tracks: '🔍 Hunting for those tracks you mentioned...',
            gathering_seeds_selecting_anchors: '🎯 Picking the perfect anchor tracks (no pressure)...',
            gathering_seeds_discovering_artists: '🔍 Unearthing hidden musical gems...',
            gathering_seeds_fetching_top_tracks: '🎧 Raiding your top tracks (with permission)...',
            gathering_seeds_fetching_top_artists: '🎤 Stalking your favorite artists (musically speaking)...',
            gathering_seeds_building_pool: '🏗️ Mixing the perfect seed cocktail...',
            gathering_seeds_analyzing_features: '🔊 Reading the audio tea leaves...',
            gathering_seeds_selecting_seeds: '🌱 Choosing seeds that will grow into bangers...',
            seeds_gathered: '✅ Seeds collected! Time to plant some musical magic...',

            // Granular sub-steps for generating_recommendations
            generating_recommendations_fetching: '🎼 Casting our musical net wide...',
            generating_recommendations_processing: '⚡ Sorting the wheat from the musical chaff...',
            generating_recommendations_diversifying: '🎨 Spicing things up with variety...',
            recommendations_generated: '✅ Fresh recommendations hot off the press!',

            // Evaluation and optimization (handles dynamic iterations like iteration_1, iteration_2, etc.)
            evaluating_quality_iteration: '🔍 Playing judge, jury, and musical executioner...',
            optimizing_recommendations_iteration: '✨ Polishing until it sparkles...',
            recommendations_ready: '✅ Recommendations locked and loaded!',
            recommendations_converged: '✅ We\'ve reached peak playlist perfection!',

            // Enrichment
            enriching_tracks: '✨ Sprinkling extra musical fairy dust...',

            // Main workflow statuses
            gathering_seeds: '🎵 Diving deep into your musical DNA...',
            generating_recommendations: '🎼 Crafting your musical masterpiece...',
            evaluating_quality: '🔍 Making sure every track earns its spot...',
            optimizing_recommendations: '✨ Fine-tuning like a musical perfectionist...',
            ordering_playlist: '🎢 Creating the perfect musical rollercoaster...',

            // Playlist creation
            playlist_created: '✅ Your playlist is born! 🎊',
            creating_playlist: '🎵 Sending your playlist to Spotify (hope they\'re ready)...',

            // User interaction
            awaiting_user_input: '✏️ Waiting for your creative genius...',
            processing_edits: '🔄 Applying your edits with surgical precision...',

            // Terminal states
            completed: '🎉 Your perfect playlist is ready to rock!',
            failed: '❌ Oops, something hit a sour note...',
            cancelled: '🚫 Workflow cancelled (no hard feelings!)',
        };

        // Check for exact match first
        if (statusMessages[statusToCheck]) {
            return statusMessages[statusToCheck];
        }

        // Check for partial matches (sub-steps)
        for (const [key, message] of Object.entries(statusMessages)) {
            if (statusToCheck.includes(key)) {
                return message;
            }
        }

        return '🎵 Cooking up something special...';
    };

    return (
        <div className="text-sm font-medium flex-1">
            {getMessage(status, currentStep)}
        </div>
    );
}

