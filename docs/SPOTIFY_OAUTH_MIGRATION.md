# Spotify OAuth Migration Guide

## Overview

As of **November 27, 2025**, Spotify has updated their OAuth requirements. This guide explains the changes we've made to ensure MoodList remains compliant.

## What Changed at Spotify

Spotify announced three major changes to their OAuth system:

1. **Implicit Grant Flow Removed**: No longer supported
2. **HTTP Redirect URIs**: No longer allowed (except for 127.0.0.1)
3. **Localhost Aliases Prohibited**: `localhost` aliases are no longer allowed

## Our Implementation

MoodList now uses **Authorization Code Flow with PKCE** (Proof Key for Code Exchange), which is the recommended approach for modern OAuth 2.0 implementations.

### Key Features

- ✅ **Authorization Code Flow with PKCE** - More secure than implicit grant
- ✅ **127.0.0.1 for Development** - Instead of `localhost` aliases
- ✅ **HTTPS for Production** - All production deployments use HTTPS redirect URIs
- ✅ **Backward Compatible** - Still supports client_secret method during transition

## What You Need to Do

### For Development

1. **Update your `.env` files** to use `127.0.0.1` instead of `localhost`:

   **Frontend** (`.env.local`):
   ```env
   NEXT_PUBLIC_BACKEND_API_URL=http://127.0.0.1:8000
   NEXT_PUBLIC_SPOTIFY_REDIRECT_URI=http://127.0.0.1:3000/callback
   ```

   **Backend** (`.env`):
   ```env
   SPOTIFY_REDIRECT_URI=http://127.0.0.1:3000/callback
   ```

2. **Update Spotify Developer Dashboard**:
   - Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
   - Select your app
   - Edit Settings → Redirect URIs
   - Remove any `http://localhost:*` entries
   - Add `http://127.0.0.1:3000/callback`
   - Click "Save"

3. **Access your app** using `http://127.0.0.1:3000` instead of `http://localhost:3000`

### For Production

1. **Ensure HTTPS redirect URIs** are configured:
   ```env
   SPOTIFY_REDIRECT_URI=https://yourdomain.com/callback
   ```

2. **Update Spotify Developer Dashboard**:
   - Add your production HTTPS redirect URI: `https://yourdomain.com/callback`
   - Remove any HTTP production URIs

## Technical Details

### PKCE Flow

Our implementation follows the OAuth 2.0 Authorization Code Flow with PKCE:

1. **Generate code_verifier**: Random cryptographic string
2. **Generate code_challenge**: SHA-256 hash of code_verifier
3. **Authorization Request**: Send `code_challenge` to Spotify
4. **Token Exchange**: Send `code_verifier` to verify the request

### Code Changes

The following files were updated:

- `frontend/src/lib/spotifyAuth.ts` - Added PKCE generation
- `frontend/src/lib/hooks/useAuthCallback.ts` - Added code_verifier handling
- `backend/app/spotify/routes.py` - Added PKCE support to token exchange
- Configuration files - Updated redirect URIs

## FAQ

### Why use 127.0.0.1 instead of localhost?

Spotify now blocks `localhost` and similar aliases. `127.0.0.1` is the actual loopback IP address and is still allowed for local development.

### Do I need to change my production setup?

If you're already using HTTPS redirect URIs in production, no changes are needed. The PKCE implementation is backward compatible.

### What happens if I don't update?

- Development: OAuth will fail if using `localhost` in redirect URIs
- Production: Should continue working if already using HTTPS

### Is PKCE required?

Yes, for new implementations. Our code supports both PKCE and client_secret for backward compatibility during the transition period, but PKCE is recommended and will be the only supported method going forward.

### Do I need to update my Spotify app settings?

Yes! You must update your redirect URIs in the Spotify Developer Dashboard to use `127.0.0.1` for development and HTTPS for production.

## Troubleshooting

### "PKCE verification failed"

- Ensure you're using the latest code
- Clear your browser's sessionStorage
- Try the authentication flow again

### "Invalid redirect URI"

- Verify your `.env` files use `127.0.0.1` (not `localhost`)
- Check Spotify Developer Dashboard has matching redirect URIs
- Ensure frontend and backend redirect URIs match

### "Authorization code is invalid"

- The authorization code may have expired
- Try the authentication flow again
- Check that code_verifier is being stored correctly

## Support

If you encounter issues after following this guide:

1. Check that all configuration files are updated
2. Clear browser cache and sessionStorage
3. Verify Spotify Developer Dashboard settings
4. Check browser console for error messages

## References

- [Spotify OAuth Migration Announcement](https://developer.spotify.com/)
- [OAuth 2.0 PKCE Specification](https://oauth.net/2/pkce/)
- [Spotify Authorization Guide](https://developer.spotify.com/documentation/web-api/concepts/authorization)
