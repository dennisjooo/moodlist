import { logger } from '@/lib/utils/logger';

const KEY_STORAGE_NAME = 'moodlist_auth_key';
const ALGORITHM = 'AES-GCM';
const KEY_LENGTH = 256;

/**
 * Generates a new AES-GCM key
 */
async function generateKey(): Promise<CryptoKey> {
    return window.crypto.subtle.generateKey(
        {
            name: ALGORITHM,
            length: KEY_LENGTH,
        },
        true,
        ['encrypt', 'decrypt']
    );
}

/**
 * Exports a key to JWK format for storage
 */
async function exportKey(key: CryptoKey): Promise<JsonWebKey> {
    return window.crypto.subtle.exportKey('jwk', key);
}

/**
 * Imports a key from JWK format
 */
async function importKey(jwk: JsonWebKey): Promise<CryptoKey> {
    return window.crypto.subtle.importKey(
        'jwk',
        jwk,
        {
            name: ALGORITHM,
            length: KEY_LENGTH,
        },
        true,
        ['encrypt', 'decrypt']
    );
}

/**
 * Gets or creates the encryption key from sessionStorage
 */
async function getEncryptionKey(): Promise<CryptoKey> {
    try {
        const storedKey = sessionStorage.getItem(KEY_STORAGE_NAME);
        if (storedKey) {
            const jwk = JSON.parse(storedKey);
            return await importKey(jwk);
        }
    } catch (error) {
        logger.warn('Failed to load encryption key, generating new one', { component: 'encryption', error });
    }

    // Generate new key if none exists or import failed
    const newKey = await generateKey();
    const jwk = await exportKey(newKey);
    sessionStorage.setItem(KEY_STORAGE_NAME, JSON.stringify(jwk));
    return newKey;
}

/**
 * Encrypts data using AES-GCM
 * Returns a string in format: "iv:encryptedData" (base64 encoded)
 */
export async function encryptData(data: unknown): Promise<string | null> {
    if (typeof window === 'undefined') return null;

    try {
        const key = await getEncryptionKey();
        const iv = window.crypto.getRandomValues(new Uint8Array(12));
        const encodedData = new TextEncoder().encode(JSON.stringify(data));

        const encryptedContent = await window.crypto.subtle.encrypt(
            {
                name: ALGORITHM,
                iv,
            },
            key,
            encodedData
        );

        // Convert to base64 strings
        const ivBase64 = btoa(String.fromCharCode(...new Uint8Array(iv)));
        const contentBase64 = btoa(String.fromCharCode(...new Uint8Array(encryptedContent)));

        return `${ivBase64}:${contentBase64}`;
    } catch (error) {
        logger.error('Encryption failed', error, { component: 'encryption' });
        return null;
    }
}

/**
 * Decrypts data using AES-GCM
 */
export async function decryptData<T>(encryptedString: string): Promise<T | null> {
    if (typeof window === 'undefined') return null;

    try {
        const [ivBase64, contentBase64] = encryptedString.split(':');
        if (!ivBase64 || !contentBase64) return null;

        const key = await getEncryptionKey();

        // Convert base64 back to arrays
        const iv = new Uint8Array(atob(ivBase64).split('').map(c => c.charCodeAt(0)));
        const content = new Uint8Array(atob(contentBase64).split('').map(c => c.charCodeAt(0)));

        const decryptedContent = await window.crypto.subtle.decrypt(
            {
                name: ALGORITHM,
                iv,
            },
            key,
            content
        );

        const decodedData = new TextDecoder().decode(decryptedContent);
        return JSON.parse(decodedData);
    } catch (error) {
        logger.error('Decryption failed', error, { component: 'encryption' });
        return null;
    }
}
