export const config = {
  api: {
    baseUrl: process.env.NEXT_PUBLIC_BACKEND_API_URL || 'http://localhost:8000',
  },
  auth: {
    sessionCookieName: 'session_token',
    cacheKey: 'moodlist_auth_cache',
    cacheTTL: 2 * 60 * 1000, // 2 minutes
  },
  polling: {
    baseInterval: 2000,
    maxBackoff: 30000,
    maxRetries: 3,
    awaitingInputInterval: 5000,
    pendingInterval: 3000,
  },
} as const;
