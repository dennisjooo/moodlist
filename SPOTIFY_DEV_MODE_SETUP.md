# Spotify Dev Mode - Limited Access UX Configuration

This document explains the limited access/dev mode features that have been added to improve the user experience when your Spotify API application is in development mode.

## Overview

When a Spotify API application is in **development mode**, it can only support up to **25 manually whitelisted users**. This creates a UX challenge because most visitors cannot actually log in.

To address this, we've implemented a comprehensive limited access notice system that:
- Clearly communicates the beta/dev mode status
- Shows informative tooltips and badges on login buttons
- Displays an alert dialog explaining the limitation before users attempt to log in
- Provides optional contact information for beta access requests

## Features Added

### 1. Configuration System (`frontend/src/lib/config.ts`)

New configuration options:
```typescript
access: {
  isDevMode: boolean;              // Enable/disable dev mode restrictions
  showLimitedAccessNotice: boolean; // Show/hide limited access UI elements
  betaContactUrl?: string;          // Optional contact URL (email, form, Discord, etc.)
  betaContactLabel?: string;        // Custom label for contact button
}
```

### 2. Enhanced Login Button

The `SpotifyLoginButton` component now:
- Shows an info icon (ℹ️) when in dev mode
- Displays a tooltip: "Limited beta - whitelisted users only"
- Opens an informational dialog before attempting login (in dev mode)
- Works seamlessly in both dev and production modes

### 3. Alert Dialog (`LimitedAccessDialog`)

Before users attempt to log in, they see a friendly dialog that:
- Explains the dev mode limitation (25 user limit)
- Clarifies that only whitelisted accounts can proceed
- Provides a "Request Access" button if you configure a contact URL
- Allows users to proceed anyway (for whitelisted users) or cancel

### 4. Visual Notices

Added subtle but clear badges in key locations:
- **Hero Section**: Banner above login button with "Limited Beta - Whitelisted users only"
- **CTA Section**: Badge in the call-to-action card
- Updated helper text to explain the private beta status

## Environment Variables

Add these to your `frontend/.env.local` file:

```bash
# Enable dev mode restrictions (default: true)
NEXT_PUBLIC_SPOTIFY_DEV_MODE=true

# Show limited access notices (default: true)
NEXT_PUBLIC_SHOW_LIMITED_ACCESS_NOTICE=true

# Optional: Provide a contact method for beta access
NEXT_PUBLIC_SPOTIFY_BETA_CONTACT_URL=mailto:your-email@example.com
# Or use a form, Discord, etc.:
# NEXT_PUBLIC_SPOTIFY_BETA_CONTACT_URL=https://forms.gle/your-form-id
# NEXT_PUBLIC_SPOTIFY_BETA_CONTACT_URL=https://discord.gg/your-invite

# Optional: Custom label for the contact button
NEXT_PUBLIC_SPOTIFY_BETA_CONTACT_LABEL=Email for Access
```

## When to Disable Dev Mode

Once your Spotify application is **approved for production** (extended quota mode), update your environment variables:

```bash
NEXT_PUBLIC_SPOTIFY_DEV_MODE=false
NEXT_PUBLIC_SHOW_LIMITED_ACCESS_NOTICE=false
```

This will:
- Remove all limited access badges and notices
- Remove the info icon from login buttons
- Skip the alert dialog - users go directly to Spotify OAuth
- Return to standard login UX

## Testing

### Test Dev Mode (Current State)
1. Ensure `NEXT_PUBLIC_SPOTIFY_DEV_MODE=true` (or not set - defaults to true)
2. Visit the home page - you should see "Limited Beta - Whitelisted users only" badge
3. Click the login button - you should see the alert dialog
4. The dialog explains the limitation and allows proceeding or canceling

### Test Production Mode
1. Set `NEXT_PUBLIC_SPOTIFY_DEV_MODE=false`
2. Visit the home page - badges/notices should be hidden
3. Click the login button - should go directly to Spotify OAuth

## Examples of Contact URLs

**Email:**
```bash
NEXT_PUBLIC_SPOTIFY_BETA_CONTACT_URL=mailto:hello@moodlist.app?subject=Beta%20Access%20Request
```

**Google Form:**
```bash
NEXT_PUBLIC_SPOTIFY_BETA_CONTACT_URL=https://forms.gle/your-form-id
NEXT_PUBLIC_SPOTIFY_BETA_CONTACT_LABEL=Fill Out Form
```

**Discord Invite:**
```bash
NEXT_PUBLIC_SPOTIFY_BETA_CONTACT_URL=https://discord.gg/your-invite
NEXT_PUBLIC_SPOTIFY_BETA_CONTACT_LABEL=Join Discord
```

**Typeform/Airtable:**
```bash
NEXT_PUBLIC_SPOTIFY_BETA_CONTACT_URL=https://your-typeform.typeform.com/to/form-id
NEXT_PUBLIC_SPOTIFY_BETA_CONTACT_LABEL=Request Beta Access
```

## Files Modified

- `frontend/src/lib/config.ts` - Added access configuration
- `frontend/src/components/features/auth/SpotifyLoginButton.tsx` - Enhanced with dev mode support
- `frontend/src/components/features/auth/LimitedAccessDialog.tsx` - New dialog component
- `frontend/src/components/features/marketing/HeroSection.tsx` - Added banner notice
- `frontend/src/components/features/marketing/CTASection.tsx` - Added badge notice
- `frontend/.env.example` - Documented new environment variables

## Future Improvements

When you're ready to expand beyond 25 users but before full approval:
- Consider adding a waitlist feature with email collection
- Implement a manual approval system where you review and add users
- Show current capacity (e.g., "15/25 slots filled")
- Add a notification system to alert users when slots open up

---

**Questions?** Feel free to reach out or modify the UX to better suit your needs!
