'use client';

import { Badge } from '@/components/ui/badge';
import { Music, Menu, X, User, LogOut } from 'lucide-react';
import { ThemeToggle } from '@/components/ThemeToggle';
import Link from 'next/link';
import { useState, useEffect } from 'react';

interface UserProfile {
  id: string;
  display_name: string;
  email: string;
  images: Array<{ url: string }>;
  country: string;
  followers: number;
}

export default function Navigation() {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [userProfile, setUserProfile] = useState<UserProfile | null>(null);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);

  // Check for existing user profile on component mount and when storage changes
  useEffect(() => {
    const checkProfile = () => {
      const profileData = localStorage.getItem('spotify_user_profile');
      const accessToken = localStorage.getItem('spotify_access_token');

      console.log('Navigation - Profile data from localStorage:', profileData);
      console.log('Navigation - Access token exists:', !!accessToken);

      if (profileData && accessToken) {
        try {
          const parsedProfile = JSON.parse(profileData);
          console.log('Navigation - Parsed profile:', parsedProfile);
          setUserProfile(parsedProfile);
          setIsLoggedIn(true);
        } catch (error) {
          console.error('Navigation - Failed to parse profile data:', error);
        }
      } else {
        setUserProfile(null);
        setIsLoggedIn(false);
      }
    };

    // Check immediately
    checkProfile();

    // Listen for storage changes (when user logs in on another tab)
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === 'spotify_user_profile' || e.key === 'spotify_access_token') {
        console.log('Navigation - Storage changed, rechecking profile');
        checkProfile();
      }
    };

    window.addEventListener('storage', handleStorageChange);

    // Also listen for custom events (when user logs in on same tab)
    const handleProfileUpdate = () => {
      console.log('Navigation - Profile update event received');
      checkProfile();
    };

    window.addEventListener('spotify-profile-update', handleProfileUpdate);

    return () => {
      window.removeEventListener('storage', handleStorageChange);
      window.removeEventListener('spotify-profile-update', handleProfileUpdate);
    };
  }, []);

  const handleLogout = () => {
    localStorage.removeItem('spotify_access_token');
    localStorage.removeItem('spotify_refresh_token');
    localStorage.removeItem('spotify_user_profile');
    setUserProfile(null);
    setIsLoggedIn(false);
    window.location.href = '/';
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
            {isLoggedIn && userProfile ? (
              <div className="flex items-center space-x-3">
                {/* Profile Dropdown */}
                <div className="relative">
                  <button
                    onClick={() => setIsDropdownOpen(!isDropdownOpen)}
                    className="flex items-center space-x-2 text-sm font-medium text-foreground hover:text-primary transition-colors"
                  >
                    {userProfile.images?.[0]?.url ? (
                      <img
                        src={userProfile.images[0].url}
                        alt={userProfile.display_name}
                        className="w-8 h-8 rounded-full"
                      />
                    ) : (
                      <div className="w-8 h-8 bg-primary/10 rounded-full flex items-center justify-center">
                        <User className="w-4 h-4 text-primary" />
                      </div>
                    )}
                    <span className="hidden sm:block max-w-24 truncate" title={userProfile.display_name}>
                      {userProfile.display_name}
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
            ) : null}

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