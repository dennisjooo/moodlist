'use client';

import { ThemeToggle } from '@/components/ThemeToggle';
import { Badge } from '@/components/ui/badge';
import { useAuth } from '@/lib/authContext';
import { initiateSpotifyAuth, isSpotifyAuthConfigured } from '@/lib/spotifyAuth';
import { LogOut, Menu, Music, User, X } from 'lucide-react';
import Link from 'next/link';
import { useEffect, useState } from 'react';
import { logger } from '@/lib/utils/logger';

export default function Navigation() {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const { user, isAuthenticated, logout, isLoading } = useAuth();

  // Only show loading if we're actually checking auth (not just initializing)
  // If isLoading is true but we have no user and no session cookie, don't show loading
  const sessionToken = typeof document !== 'undefined' && document.cookie.includes('session_token');
  const shouldShowLoading = isLoading && (user !== null || sessionToken);

  if (shouldShowLoading) {
    return (
      <nav className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="w-8 h-8 bg-primary/20 rounded-lg animate-pulse"></div>
          </div>
        </div>
      </nav>
    );
  }

  // Listen for auth updates
  useEffect(() => {
    const handleAuthUpdate = () => {
      // Force re-render when auth state changes
      window.location.reload();
    };

    window.addEventListener('auth-update', handleAuthUpdate);
    return () => {
      window.removeEventListener('auth-update', handleAuthUpdate);
    };
  }, []);

  const handleLogout = async () => {
    try {
      await logout();
      setIsDropdownOpen(false);
      setIsMenuOpen(false);
      // Force page reload to clear any cached state
      window.location.href = '/';
    } catch (error) {
      logger.error('Logout failed', error, { component: 'Navigation' });
      // Even if backend logout fails, redirect to clear frontend state
      window.location.href = '/';
    }
  };

  const navItems = [
    { name: 'Home', href: '/' },
    { name: 'Create', href: '/create' },
    { name: 'My Playlists', href: '/playlists' },
    { name: 'About', href: '/about' },
  ];

  return (
    <nav className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16 lg:justify-center lg:relative">
          {/* Logo - Left Side */}
          <div className="lg:absolute lg:left-0">
            <Link href="/" className="flex items-center space-x-3">
              <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
                <Music className="w-4 h-4 text-primary-foreground" />
              </div>
              <span className="font-semibold text-xl">MoodList</span>
              <Badge variant="secondary" className="ml-2">Beta</Badge>
            </Link>
          </div>

          {/* Desktop Navigation Links - Center */}
          <div className="hidden lg:flex items-center space-x-8">
            {navItems.map((item) => (
              <Link
                key={item.name}
                href={item.href}
                className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
              >
                {item.name}
              </Link>
            ))}
          </div>

          {/* Right Side - Profile & Mobile Menu Button */}
          <div className="flex items-center space-x-4 lg:absolute lg:right-0">
            {isAuthenticated && user ? (
              <div className="flex items-center space-x-3">
                {/* Profile Dropdown */}
                <div className="relative">
                  <button
                    onClick={() => setIsDropdownOpen(!isDropdownOpen)}
                    className="flex items-center space-x-2 text-sm font-medium text-foreground hover:text-primary transition-colors"
                  >
                    {user.profile_image_url ? (
                      <img
                        src={user.profile_image_url}
                        alt={user.display_name}
                        className="w-8 h-8 rounded-full"
                      />
                    ) : (
                      <div className="w-8 h-8 bg-primary/10 rounded-full flex items-center justify-center">
                        <User className="w-4 h-4 text-primary" />
                      </div>
                    )}
                    <span className="hidden sm:block max-w-24 truncate" title={user.display_name}>
                      {user.display_name}
                    </span>
                  </button>

                  {/* Dropdown Menu */}
                  {isDropdownOpen && (
                    <div className="absolute right-0 top-full mt-2 w-48 bg-background border rounded-lg shadow-lg z-50">
                      <div className="p-2">
                        <Link
                          href="/profile"
                          onClick={() => setIsDropdownOpen(false)}
                          className="w-full flex items-center space-x-2 px-3 py-2 text-sm text-foreground hover:bg-accent rounded-md transition-colors"
                        >
                          <User className="w-4 h-4" />
                          <span>View Profile</span>
                        </Link>
                        <hr className="my-1" />
                        <button
                          onClick={() => {
                            handleLogout();
                            setIsDropdownOpen(false);
                          }}
                          className="w-full flex items-center justify-center space-x-2 px-3 py-2 text-sm text-red-600 hover:bg-red-50 rounded-md transition-colors"
                        >
                          <LogOut className="w-4 h-4" />
                          <span>Sign Out</span>
                        </button>
                      </div>
                    </div>
                  )}

                  {/* Click outside to close */}
                  {isDropdownOpen && (
                    <div
                      className="fixed inset-0 z-40"
                      onClick={() => setIsDropdownOpen(false)}
                    />
                  )}
                </div>
              </div>
            ) : (
              <button
                onClick={() => {
                  if (!isSpotifyAuthConfigured()) {
                    return;
                  }
                  initiateSpotifyAuth();
                }}
                className="bg-[#1DB954] hover:bg-[#1ed760] text-white h-10 px-6 rounded-md font-medium transition-all duration-200 flex items-center gap-2 shadow-md hover:shadow-lg hidden lg:flex"
              >
                <svg
                  className="w-4 h-4"
                  viewBox="0 0 24 24"
                  fill="currentColor"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.42 1.56-.299.421-1.02.599-1.559.3z"/>
                </svg>
                Login
              </button>
            )}

            {/* Theme Toggle - Hidden on mobile */}
            <div className="hidden lg:block">
              <ThemeToggle />
            </div>

            {/* Mobile Menu Button */}
            <button
              onClick={() => setIsMenuOpen(!isMenuOpen)}
              className="lg:hidden p-2 rounded-md text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
              aria-label="Toggle menu"
            >
              {isMenuOpen ? (
                <X className="w-5 h-5" />
              ) : (
                <Menu className="w-5 h-5" />
              )}
            </button>
          </div>
        </div>

        {/* Mobile Menu */}
        <div className={`lg:hidden border-t bg-background/95 backdrop-blur overflow-hidden transition-all duration-300 ease-in-out ${
          isMenuOpen ? 'max-h-64 opacity-100' : 'max-h-0 opacity-0'
        }`}>
          <div className="px-2 pt-2 pb-3 space-y-1">
            {navItems.map((item, index) => (
              <Link
                key={item.name}
                href={item.href}
                className={`block px-3 py-2 rounded-md text-sm font-medium text-muted-foreground hover:text-foreground hover:bg-accent transition-all duration-200 transform ${
                  isMenuOpen
                    ? 'translate-x-0 opacity-100'
                    : '-translate-x-4 opacity-0'
                }`}
                style={{
                  transitionDelay: isMenuOpen ? `${index * 50}ms` : '0ms'
                }}
                onClick={() => setIsMenuOpen(false)}
              >
                {item.name}
              </Link>
            ))}

            {/* Profile Link in Mobile Menu */}
            {isAuthenticated && user ? (
              <Link
                href="/profile"
                className={`block px-3 py-2 rounded-md text-sm font-medium text-foreground hover:bg-accent transition-all duration-200 transform ${
                  isMenuOpen
                    ? 'translate-x-0 opacity-100'
                    : '-translate-x-4 opacity-0'
                }`}
                style={{
                  transitionDelay: isMenuOpen ? `${(navItems.length - 1) * 50}ms` : '0ms'
                }}
                onClick={() => setIsMenuOpen(false)}
              >
                <div className="flex items-center space-x-2">
                  <User className="w-4 h-4" />
                  <span>View Profile</span>
                </div>
              </Link>
            ) : (
              <button
                onClick={() => {
                  if (!isSpotifyAuthConfigured()) {
                    return;
                  }
                  initiateSpotifyAuth();
                }}
                className={`w-full text-left block px-3 py-2 rounded-md text-sm font-medium text-foreground hover:bg-accent transition-all duration-200 transform ${
                  isMenuOpen
                    ? 'translate-x-0 opacity-100'
                    : '-translate-x-4 opacity-0'
                }`}
                style={{
                  transitionDelay: isMenuOpen ? `${(navItems.length - 1) * 50}ms` : '0ms'
                }}
              >
                <div className="flex items-center space-x-2">
                  <svg
                    className="w-4 h-4"
                    viewBox="0 0 24 24"
                    fill="currentColor"
                    xmlns="http://www.w3.org/2000/svg"
                  >
                    <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.42 1.56-.299.421-1.02.599-1.559.3z"/>
                  </svg>
                  <span>Login</span>
                </div>
              </button>
            )}

            {/* Theme Toggle in Mobile Menu */}
            <div className={`transform ${
              isMenuOpen
                ? 'translate-x-0 opacity-100'
                : '-translate-x-4 opacity-0'
            }`}
            style={{
              transitionDelay: isMenuOpen ? `${navItems.length * 50}ms` : '0ms'
            }}>
              <div className="px-3 py-2">
                <ThemeToggle />
              </div>
            </div>
          </div>
        </div>
      </div>
    </nav>
  );
}