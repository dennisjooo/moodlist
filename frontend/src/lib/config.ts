interface APIConfig {
  readonly baseUrl: string;
}

interface AuthConfig {
  readonly sessionCookieName: string;
  readonly cacheKey: string;
  readonly cacheTTL: number;
}

interface PollingConfig {
  readonly baseInterval: number;
  readonly maxBackoff: number;
  readonly maxRetries: number;
  readonly awaitingInputInterval: number;
  readonly pendingInterval: number;
}

export interface AppConfig {
  readonly api: APIConfig;
  readonly auth: AuthConfig;
  readonly polling: PollingConfig;
}

export const config: AppConfig = {
  api: {
    baseUrl: process.env.NEXT_PUBLIC_BACKEND_API_URL || 'http://localhost:8000',
  },
  auth: {
    sessionCookieName: 'session_token',
    cacheKey: 'moodlist_auth_cache',
    cacheTTL: 24 * 60 * 60 * 1000, // 24 hours - matches session expiration
  },
  polling: {
    baseInterval: 3000,          // 3s
    maxBackoff: 30000,           // 30s
    maxRetries: 3,
    awaitingInputInterval: 10000, // 10s
    pendingInterval: 5000,        // 5s
  },
};
