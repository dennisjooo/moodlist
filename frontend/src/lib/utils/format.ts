export const formatDuration = (ms: number): string => {
    const minutes = Math.floor(ms / 60000);
    const seconds = Math.floor((ms % 60000) / 1000);
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
};

export const formatReleaseDate = (dateString: string): string => {
    if (!dateString) return 'Unknown';
    const parts = dateString.split('-');
    if (parts.length === 1) return parts[0];
    if (parts.length === 2) return `${parts[1]}/${parts[0]}`;
    return new Date(dateString).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
    });
};

