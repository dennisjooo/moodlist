/**
 * Frontend cookie utility functions for reading HttpOnly cookies
 */

/**
 * Get a cookie value by name
 */
export function getCookie(name: string): string | null {
  if (typeof document === 'undefined') {
    return null; // Server-side rendering
  }

  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) {
    const cookieValue = parts.pop()?.split(';').shift() || null;
    return cookieValue;
  }
  return null;
}

/**
 * Check if user is authenticated by checking for session cookie
 */
export function isAuthenticated(): boolean {
  const sessionToken = getCookie('session_token');
  return Boolean(sessionToken);
}

/**
 * Get authentication cookies for API requests
 */
export function getAuthCookies(): Record<string, string> {
  const sessionToken = getCookie('session_token');
  return sessionToken ? { 'Cookie': `session_token=${sessionToken}` } : {};
}