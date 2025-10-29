'use client';

import { SpotifyLoginButton } from '@/components/features/auth/SpotifyLoginButton';
import { Button } from '@/components/ui/button';
import { motion } from '@/components/ui/lazy-motion';
import { CheckCircle2 } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { useAuth } from '@/lib/contexts/AuthContext';
import { CTA_HIGHLIGHTS } from '@/lib/constants/marketing';

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

  const isLoggedIn = isClient ? isAuthenticated : serverIsLoggedIn;

  return (
    <section className="relative mt-20">
      <div className="absolute inset-0 -z-10">
        <div className="mx-auto h-full max-w-6xl rounded-3xl bg-gradient-to-br from-primary/15 via-primary/5 to-transparent blur-2xl" />
      </div>
      <div className="mx-auto max-w-6xl rounded-3xl border border-white/10 bg-background/80 px-6 py-16 shadow-[0_30px_100px_-45px_rgba(59,130,246,0.55)] backdrop-blur sm:px-12 md:py-20">
        <div className="flex flex-col gap-10 md:flex-row md:items-center md:justify-between">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: '-50px' }}
            transition={{ duration: 0.6, ease: 'easeOut' }}
            className="md:max-w-xl"
          >
            <p className="text-sm font-semibold uppercase tracking-[0.2em] text-primary">Ready when you are</p>
            <h2 className="mt-3 text-3xl font-semibold sm:text-4xl">
              Turn today&apos;s mood into tonight&apos;s soundtrack
            </h2>
            <p className="mt-4 text-base text-muted-foreground">
              Describe how you feel and Moodlist will translate it into a fully fledged playlist. Start with a vibe, keep what you love, and save the rest for later.
            </p>
            <ul className="mt-6 space-y-3">
              {CTA_HIGHLIGHTS.map((highlight) => (
                <li key={highlight} className="flex items-start gap-3 text-sm text-muted-foreground sm:text-base">
                  <CheckCircle2 className="mt-0.5 h-5 w-5 text-primary" />
                  <span>{highlight}</span>
                </li>
              ))}
            </ul>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: '-50px' }}
            transition={{ duration: 0.6, delay: 0.1, ease: 'easeOut' }}
            className="flex w-full max-w-sm flex-col gap-4 rounded-2xl border border-border/60 bg-background/90 p-6 text-center shadow-lg"
          >
            <p className="text-sm font-medium text-muted-foreground">
              {isLoggedIn ? 'Jump back in and create another mix.' : 'Connect Spotify to start crafting playlists.'}
            </p>
            {isClient ? (
              isLoggedIn ? (
                <Button size="lg" className="w-full" onClick={() => router.push('/create')}>
                  Create a playlist
                </Button>
              ) : (
                <SpotifyLoginButton data-cta="true" />
              )
            ) : (
              <div className="h-11 w-full animate-pulse rounded-lg bg-muted" />
            )}
            <p className="text-xs text-muted-foreground">
              No algorithms chasing clicks—just music built around your mood.
            </p>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
