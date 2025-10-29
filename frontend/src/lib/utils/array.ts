/**
 * Array utility functions
 */

/**
 * Shuffles an array using the Fisher-Yates algorithm
 * Returns a new array without modifying the original
 */
export function shuffleArray<T>(array: T[]): T[] {
    const shuffled = [...array];
    for (let i = shuffled.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
    }
    return shuffled;
}

/**
 * Gets a random index from an array
 * @param array The array to get a random index from
 * @returns A random index between 0 and array.length - 1
 */
export function getRandomIndex<T>(array: T[]): number {
    if (array.length === 0) return 0;
    return Math.floor(Math.random() * array.length);
}

/**
 * Gets a random item from an array
 * @param array The array to get a random item from
 * @returns A random item from the array, or undefined if array is empty
 */
export function getRandomItem<T>(array: T[]): T | undefined {
    if (array.length === 0) return undefined;
    return array[getRandomIndex(array)];
}

