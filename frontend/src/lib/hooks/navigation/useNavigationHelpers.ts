'use client';

import { useRouter } from 'next/navigation';
import { useCallback } from 'react';

/**
 * Custom hook for common navigation patterns
 * 
 * Provides helpers for:
 * - Smart back navigation
 * - Edit page navigation
 * - Playlist navigation
 */
export function useNavigationHelpers() {
  const router = useRouter();

  /**
   * Smart back navigation that considers referrer and current context
   */
  const handleSmartBack = useCallback((sessionId?: string) => {
    // Check if we're currently on an edit page - if so, go back to the parent create page
    if (window.location.pathname.includes('/edit')) {
      const parentPath = window.location.pathname.replace('/edit', '');
      router.push(parentPath);
      return;
    }

    // Determine navigation origin and destination
    const referrer = document.referrer;
    const currentPath = window.location.pathname;

    // If user came from playlists page, go back there
    if (referrer.includes('/playlists')) {
      router.push('/playlists');
    }
    // If user came from /create page, go back there
    else if (referrer.includes('/create') && !referrer.includes('/create/')) {
      router.push('/create');
    }
    // If referrer is unclear but we have a session ID, user likely came from playlists
    else if (currentPath.includes('/create/') && sessionId) {
      router.push('/playlists');
    }
    // Default fallback to playlists
    else {
      router.push('/playlists');
    }
  }, [router]);

  /**
   * Navigate to edit page for a playlist
   */
  const navigateToEdit = useCallback((sessionId: string) => {
    router.push(`/playlist/${sessionId}/edit`);
  }, [router]);

  /**
   * Navigate to playlist view page
   */
  const navigateToPlaylist = useCallback((sessionId: string) => {
    router.push(`/playlist/${sessionId}`);
  }, [router]);

  /**
   * Navigate to create page (optionally with mood)
   */
  const navigateToCreate = useCallback((mood?: string) => {
    if (mood) {
      router.push(`/create?mood=${encodeURIComponent(mood)}`);
    } else {
      router.push('/create');
    }
  }, [router]);

  /**
   * Navigate to playlists list
   */
  const navigateToPlaylists = useCallback(() => {
    router.push('/playlists');
  }, [router]);

  return {
    handleSmartBack,
    navigateToEdit,
    navigateToPlaylist,
    navigateToCreate,
    navigateToPlaylists,
    router, // Expose router for custom navigation
  };
}

