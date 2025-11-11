'use client';

import { SpotifyLoginButton } from '@/components/features/auth/SpotifyLoginButton';
import { Button } from '@/components/ui/button';
import { motion } from '@/components/ui/lazy-motion';
import { CheckCircle2, Info } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { useAuth } from '@/lib/store/authStore';
import { CTA_HIGHLIGHTS } from '@/lib/constants/marketing';
import { config } from '@/lib/config';

export interface CTASectionProps {
  isLoggedIn?: boolean;
}

export default function CTASection({ isLoggedIn: serverIsLoggedIn }: CTASectionProps) {
  const router = useRouter();
  const { isAuthenticated } = useAuth();
  const [isClient, setIsClient] = useState(false);

  useEffect(() => {
    setIsClient(true);
  }, []);

  // Use client-side auth state when available, fall back to server prop (if provided)
  // In cross-origin setups, serverIsLoggedIn may be undefined/unreliable
  const isLoggedIn = isClient ? isAuthenticated : (serverIsLoggedIn ?? false);

  return (
    <section className="relative mt-12 px-4 sm:mt-16 sm:px-6 md:mt-20 lg:px-8">
      <div className="absolute inset-0 -z-10 px-4 sm:px-6 lg:px-8">
        <div className="mx-auto h-full max-w-6xl rounded-2xl bg-gradient-to-br from-primary/15 via-primary/5 to-transparent blur-2xl sm:rounded-3xl" />
      </div>
      <div className="mx-auto max-w-6xl rounded-2xl border border-white/10 bg-background/80 px-6 py-12 shadow-[0_20px_80px_-35px_rgba(59,130,246,0.55)] backdrop-blur sm:rounded-3xl sm:px-8 sm:py-14 md:px-12 md:py-20 md:shadow-[0_30px_100px_-45px_rgba(59,130,246,0.55)]">
        <div className="flex flex-col gap-8 sm:gap-10 md:flex-row md:items-center md:justify-between">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: '-50px' }}
            transition={{ duration: 0.6, ease: 'easeOut' }}
            className="md:max-w-xl"
          >
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-primary sm:text-sm">Ready when you are</p>
            <h2 className="mt-2 text-2xl font-semibold leading-tight sm:mt-3 sm:text-3xl md:text-4xl">
              Turn today&apos;s mood into tonight&apos;s soundtrack
            </h2>
            <p className="mt-3 text-sm leading-relaxed text-muted-foreground sm:mt-4 sm:text-base">
              Describe how you feel and Moodlist will translate it into a fully fledged playlist. Start with a vibe, keep what you love, and save the rest for later.
            </p>
            <ul className="mt-5 space-y-2.5 sm:mt-6 sm:space-y-3">
              {CTA_HIGHLIGHTS.map((highlight) => (
                <li key={highlight} className="flex items-start gap-2.5 text-sm text-muted-foreground sm:gap-3 sm:text-base">
                  <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-primary sm:h-5 sm:w-5" />
                  <span className="leading-snug">{highlight}</span>
                </li>
              ))}
            </ul>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: '-50px' }}
            transition={{ duration: 0.6, delay: 0.1, ease: 'easeOut' }}
            className="flex w-full flex-col gap-3.5 rounded-xl border border-border/60 bg-background/90 p-5 text-center shadow-lg sm:gap-4 sm:rounded-2xl sm:p-6 md:max-w-sm"
          >
            <p className="text-xs font-medium leading-relaxed text-muted-foreground sm:text-sm">
              {isLoggedIn ? 'Jump back in and create another mix.' : 'Connect Spotify to start crafting playlists.'}
            </p>
            {isClient ? (
              isLoggedIn ? (
                <Button size="lg" className="h-11 w-full text-base sm:h-12" onClick={() => router.push('/create')}>
                  Create a playlist
                </Button>
              ) : (
                <SpotifyLoginButton className="bg-[#1DB954] hover:bg-[#1ed760] text-white h-11 w-full px-6 rounded-md font-medium transition-all duration-200 flex items-center justify-center gap-2 shadow-md hover:shadow-lg sm:h-12 text-base" data-cta="true" />
              )
            ) : (
              <div className="h-11 w-full animate-pulse rounded-lg bg-muted sm:h-12" />
            )}
            <p className="text-[11px] leading-relaxed text-muted-foreground sm:text-xs">
              No algorithms chasing clicks—just music built around your mood.
            </p>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
