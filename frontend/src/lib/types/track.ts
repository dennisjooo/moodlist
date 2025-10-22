export interface Track {
    track_id: string;
    track_name: string;
    artists: string[];
    confidence_score: number;
    spotify_uri?: string;
}
