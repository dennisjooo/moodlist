/**
 * Status messages for workflow steps and sub-steps
 * These messages provide user-friendly feedback during playlist creation
 */
export const WORKFLOW_STATUS_MESSAGES: Record<string, string> = {
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
    gathering_seeds_tracks_fetched: '✅ Got your top tracks! Moving on...',
    gathering_seeds_fetching_top_artists: '🎤 Stalking your favorite artists (musically speaking)...',
    gathering_seeds_artists_fetched: '✅ Found your fave artists! Continuing...',
    gathering_seeds_building_pool: '🏗️ Mixing the perfect seed cocktail...',
    gathering_seeds_analyzing_features: '🔊 Reading the audio tea leaves...',
    gathering_seeds_features_analyzed: '✅ Audio features decoded! Next up...',
    gathering_seeds_selecting_seeds: '🌱 Choosing seeds that will grow into bangers...',
    gathering_seeds_tracks_scored: '✅ Tracks scored and ranked! Almost there...',
    seeds_gathered: '✅ Seeds collected! Time to plant some musical magic...',

    // Granular sub-steps for generating_recommendations
    generating_recommendations_fetching: '🎼 Casting our musical net wide...',
    generating_recommendations_anchors: '⚓ Adding your anchor tracks first...',
    generating_recommendations_fetched: '📥 Downloaded a treasure trove of possibilities...',
    generating_recommendations_processing_artists: '🎨 Exploring artists one by one...',
    generating_recommendations_processing: '⚡ Sorting the wheat from the musical chaff...',
    generating_recommendations_processed: '✅ Filtered down to the cream of the crop...',
    generating_recommendations_diversifying: '🎨 Spicing things up with variety...',
    generating_recommendations_streaming: '📡 Streaming fresh tracks your way...',
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

/**
 * Get a status message for a given status string
 * Handles exact matches first, then partial matches for sub-steps
 */
export function getWorkflowStatusMessage(status: string | null): string {
    if (!status) return '🎵 Preparing something magical for you...';

    // Check for exact match first
    if (WORKFLOW_STATUS_MESSAGES[status]) {
        return WORKFLOW_STATUS_MESSAGES[status];
    }

    // Check for partial matches (sub-steps)
    for (const [key, message] of Object.entries(WORKFLOW_STATUS_MESSAGES)) {
        if (status.includes(key)) {
            return message;
        }
    }

    return '🎵 Cooking up something special...';
}
