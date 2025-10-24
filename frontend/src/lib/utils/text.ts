/**
 * Clean text by removing special characters and unwanted content
 */
export function cleanText(text: string): string {
    return text
        .replace(/\n/g, ' ') // Remove newlines
        .replace(/\r/g, ' ') // Remove carriage returns
        .replace(/\t/g, ' ') // Remove tabs
        .replace(/\s+/g, ' ') // Normalize multiple spaces
        .replace(/[^\w\s\-.,!?']/g, '') // Remove special characters but keep basic punctuation
        .trim();
}
