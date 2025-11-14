'use client';

import { SpotifyLoginButton } from '@/components/features/auth/SpotifyLoginButton';
import TypewriterText from '@/components/TypewriterText';
import { Button } from '@/components/ui/button';
import { FeatureBadge } from '@/components/ui/feature-badge';
import { config } from '@/lib/config';
import { useAuth } from '@/lib/store/authStore';
import { ArrowDown, Music } from 'lucide-react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useEffect, useState } from 'react';

export interface HeroSectionProps {
    isLoggedIn?: boolean;
}

export function HeroSection({ isLoggedIn: serverIsLoggedIn }: HeroSectionProps) {
    const router = useRouter();
    const searchParams = useSearchParams();
    const [isClient, setIsClient] = useState(false);
    const { isAuthenticated } = useAuth();

    // Use client-side auth state when available, fall back to server prop (if provided)
    // In cross-origin setups, serverIsLoggedIn may be undefined/unreliable
    const isLoggedIn = isClient ? isAuthenticated : (serverIsLoggedIn ?? false);

    useEffect(() => {
        setIsClient(true);

        // Handle auth=required query parameter
        const authRequired = searchParams.get('auth') === 'required';
        const redirectPath = searchParams.get('redirect');

        if (authRequired && !isAuthenticated && isClient) {
            // Store redirect URL for after authentication
            if (redirectPath) {
                sessionStorage.setItem('auth_redirect', decodeURIComponent(redirectPath));
            }

            // Clear the auth query params from URL without triggering a navigation
            const newUrl = new URL(window.location.href);
            newUrl.searchParams.delete('auth');
            newUrl.searchParams.delete('redirect');
            window.history.replaceState({}, '', newUrl.toString());

            // Auto-trigger login after a brief delay to allow UI to render
            setTimeout(() => {
                const loginButton = document.querySelector('[data-spotify-login]') as HTMLButtonElement;
                if (loginButton) {
                    loginButton.click();
                }
            }, 100);
        }
    }, [searchParams, isAuthenticated, isClient]);

    return (
        <div className="relative h-screen flex items-center justify-center px-6 lg:px-8">
            <div className="max-w-7xl mx-auto w-full">
                <div className="flex flex-col items-center text-center justify-center h-full">
                    <div className="mb-8">
                        <FeatureBadge icon={Music}>
                            AI-Powered Playlist Generation
                        </FeatureBadge>
                    </div>

                    <h1 className="text-4xl font-bold tracking-tight text-foreground sm:text-6xl lg:text-7xl mb-8">
                        Turn your mood into<br />{' '}
                        <span className="bg-gradient-to-r from-primary to-primary bg-clip-text text-transparent">
                            <TypewriterText
                                strings={[
                                    'music',
                                    'playlists',
                                    'vibes',
                                    'soundtracks',
                                    'beats'
                                ]}
                                className="inline-block"
                            />
                        </span>
                    </h1>
                    <p className="text-lg leading-8 text-muted-foreground max-w-3xl mb-12">
                        Describe how you&apos;re feeling and we&apos;ll create the perfect Spotify playlist for your moment.
                        <br />
                        Powered by AI, personalized for you.
                    </p>

                    <div className="flex flex-col items-center mb-16">
                        {!isClient ? (
                            <div className="flex flex-col items-center space-y-4 min-h-[120px] justify-center">
                                {/* Placeholder to prevent layout shift during hydration */}
                                <div className="h-12 w-64" />
                            </div>
                        ) : !isLoggedIn ? (
                            <div className="flex flex-col items-center space-y-4 min-h-[120px] justify-center">
                                <SpotifyLoginButton />
                                <p className="text-sm text-muted-foreground text-center max-w-sm">
                                    {config.access.isDevMode && config.access.showLimitedAccessNotice
                                        ? 'We\'re in private beta for now. Let\'s hope give it a try if you\'re interested.'
                                        :'Connect your Spotify account to get started'}
                                </p>
                            </div>
                        ) : (
                            <div className="w-full max-w-md min-h-[120px] flex items-center justify-center">
                                <Button
                                    onClick={() => router.push('/create')}
                                    className="w-full"
                                    size="lg"
                                >
                                    Create Playlist
                                </Button>
                            </div>
                        )}
                    </div>

                    {/* Learn More Arrow */}
                    <div className="flex flex-col items-center space-y-2 text-muted-foreground">
                        <ArrowDown className="w-6 h-6" />
                    </div>
                </div>
            </div>
        </div>
    );
}

