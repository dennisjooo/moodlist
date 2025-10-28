export const config = {
  api: {
    baseUrl: process.env.NEXT_PUBLIC_BACKEND_API_URL || 'http://localhost:8000',
  },
  auth: {
    sessionCookieName: 'session_token',
    cacheKey: 'moodlist_auth_cache',
    cacheTTL: 24 * 60 * 60 * 1000, // 24 hours - matches session expiration
  },
  polling: {
    baseInterval: 3000,          // Reduced frequency: 3s (was 2s)
    maxBackoff: 30000,
    maxRetries: 3,
    awaitingInputInterval: 10000, // Reduced frequency: 10s (was 5s)
    pendingInterval: 5000,        // Reduced frequency: 5s (was 3s)
  },
} as const;
