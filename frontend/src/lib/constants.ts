export const ROUTES = {
  HOME: '/',
  CREATE: '/create',
  PLAYLISTS: '/playlists',
  PLAYLIST: '/playlist',
  PROFILE: '/profile',
  CALLBACK: '/callback',
  ABOUT: '/about',
} as const;

export const TIMING = {
  POLLING_INTERVAL: 2000,
  POLLING_INTERVAL_WAITING: 5000,
  AUTH_CACHE_TTL: 2 * 60 * 1000,
  TOAST_DURATION: 3000,
  ANIMATION_DELAY: 100,
} as const;

export const COOKIES = {
  SESSION_TOKEN: 'session_token',
} as const;
