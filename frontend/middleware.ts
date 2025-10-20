import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

// Routes that require authentication
// Note: We deliberately do NOT protect the base "/create" route to preserve
// the existing UX where unauthenticated users can see the mood input and be
// prompted to log in only when they try to start a workflow.
const PROTECTED_ROUTE_CHECK = (pathname: string) => {
  // Protect dynamic create routes like /create/<id>
  if (pathname.startsWith('/create/')) return true;
  if (pathname.startsWith('/playlists')) return true;
  if (pathname.startsWith('/playlist')) return true;
  if (pathname.startsWith('/profile')) return true;
  return false;
};

// Routes to exclude from auth checks
const PUBLIC_ROUTES = [
  '/callback', // Spotify OAuth callback
  '/api', // API routes handle their own auth
  '/_next', // Next.js internals
];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Skip auth check for public routes
  if (PUBLIC_ROUTES.some((route) => pathname.startsWith(route))) {
    return NextResponse.next();
  }

  // Check if route requires authentication
  const requiresAuth = PROTECTED_ROUTE_CHECK(pathname);

  if (!requiresAuth) {
    return NextResponse.next();
  }

  // Check for session token in cookies
  const sessionToken = request.cookies.get('session_token');

  if (!sessionToken) {
    // No session cookie - redirect to home with auth required flag
    const url = request.nextUrl.clone();
    url.pathname = '/';
    url.searchParams.set('auth', 'required');
    url.searchParams.set('redirect', pathname);

    return NextResponse.redirect(url);
  }

  // Session cookie exists - allow through
  // (Client-side will verify validity in the background)
  return NextResponse.next();
}

export const config = {
  matcher: [
    // Match all request paths except for Next.js internals and static assets
    '/((?!_next/static|_next/image|favicon.ico).*)',
  ],
};
