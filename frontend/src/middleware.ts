import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

// Protected routes that require authentication
const PROTECTED_ROUTES = [
    '/create',
    '/playlists',
    '/playlist',
    '/profile',
];

// Routes that should be excluded from auth checks
const EXCLUDED_ROUTES = [
    '/callback',
    '/api',
    '/_next',
    '/favicon.ico',
];

export function middleware(request: NextRequest) {
    const { pathname } = request.nextUrl;

    // Skip middleware for excluded routes
    if (EXCLUDED_ROUTES.some(route => pathname.startsWith(route))) {
        return NextResponse.next();
    }

    // Check if the current path is a protected route
    const isProtectedRoute = PROTECTED_ROUTES.some(route => pathname.startsWith(route));

    if (isProtectedRoute) {
        // Check for session cookie
        const sessionToken = request.cookies.get('session_token');

        if (!sessionToken) {
            // No session cookie - redirect to home with auth required query param
            const url = request.nextUrl.clone();
            url.pathname = '/';
            url.searchParams.set('auth', 'required');
            url.searchParams.set('redirect', pathname);

            return NextResponse.redirect(url);
        }
    }

    return NextResponse.next();
}

// Configure which routes use this middleware
export const config = {
    matcher: [
        /*
         * Match all request paths except for the ones starting with:
         * - api (API routes)
         * - _next/static (static files)
         * - _next/image (image optimization files)
         * - favicon.ico (favicon file)
         */
        '/((?!api|_next/static|_next/image|favicon.ico).*)',
    ],
};

