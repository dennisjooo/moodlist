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

interface AccessConfig {
  readonly isDevMode: boolean;
  readonly showLimitedAccessNotice: boolean;
  readonly betaContactUrl?: string;
  readonly betaContactLabel?: string;
}

export interface AppConfig {
  readonly api: APIConfig;
  readonly auth: AuthConfig;
  readonly polling: PollingConfig;
  readonly access: AccessConfig;
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
  access: {
    // Spotify API in dev mode = limited to 25 manually added users
    isDevMode: process.env.NEXT_PUBLIC_SPOTIFY_DEV_MODE !== 'false',
    showLimitedAccessNotice: process.env.NEXT_PUBLIC_SHOW_LIMITED_ACCESS_NOTICE !== 'false',
    betaContactUrl: process.env.NEXT_PUBLIC_SPOTIFY_BETA_CONTACT_URL || undefined,
    betaContactLabel: process.env.NEXT_PUBLIC_SPOTIFY_BETA_CONTACT_LABEL || undefined,
  },
};
