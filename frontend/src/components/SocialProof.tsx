"use client";

import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { motion } from '@/components/ui/lazy-motion';
import { useEffect, useRef, useState } from 'react';
import { config } from '@/lib/config';
import { logger } from '@/lib/utils/logger';

interface PublicStats {
  total_users: number;
  total_playlists: number;
  completed_playlists: number;
}

export default function SocialProof() {
  const containerRef = useRef(null);
  const [stats, setStats] = useState<PublicStats | null>(null);
  const [loading, setLoading] = useState(true);

  // Generate consistent fake avatars using DiceBear API
  // This is privacy-friendly - we don't expose real user data!
  const avatarSeeds = ['Felix', 'Aneka', 'Luna', 'Charlie', 'Max'];
  const avatarStyles = ['adventurer', 'avataaars', 'bottts', 'fun-emoji', 'lorelei'];

  useEffect(() => {
    async function fetchStats() {
      try {
        const response = await fetch(`${config.api.baseUrl}/api/stats/public`);
        if (response.ok) {
          const data = await response.json();
          setStats(data);
        }
      } catch (error) {
        logger.error('Failed to fetch public stats', error, { component: 'SocialProof' });
      } finally {
        setLoading(false);
      }
    }

    fetchStats();
  }, []);

  // Format numbers with commas
  const formatNumber = (num: number) => {
    if (num >= 1000) {
      return `${(num / 1000).toFixed(1)}k+`;
    }
    return num.toString();
  };

  // Get display text for playlists
  const getPlaylistsText = () => {
    if (!stats) return '1,000+ playlists created';
    const count = stats.total_playlists;
    if (count === 0) return 'Be the first to create a playlist!';
    return `${formatNumber(count)} playlists created`;
  };

  // Determine number of avatars to show based on user count
  const getAvatarCount = () => {
    if (!stats || stats.total_users === 0) return 0;
    return Math.min(stats.total_users, 5);
  };

  return (
    <div ref={containerRef} className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mt-16 pb-16">
      <div className="flex flex-col items-center text-center">
        <motion.p
          className="text-sm text-muted-foreground mb-6"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-50px" }}
          transition={{ duration: 0.6, ease: "easeOut" }}
        >
          Trusted by music lovers
        </motion.p>
        <motion.div
          className="flex items-center space-x-4"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-50px" }}
          transition={{ duration: 0.6, delay: 0.2, ease: "easeOut" }}
        >
          <div className="flex -space-x-2">
            {loading ? (
              // Show loading placeholders
              [1, 2, 3, 4, 5].map((i) => (
                <Avatar key={i} className="border-2 border-background">
                  <AvatarFallback className="text-xs bg-muted animate-pulse" />
                </Avatar>
              ))
            ) : getAvatarCount() > 0 ? (
              // Show fake avatars using DiceBear (privacy-friendly!)
              avatarSeeds.slice(0, getAvatarCount()).map((seed, i) => {
                const style = avatarStyles[i % avatarStyles.length];
                return (
                  <Avatar key={i} className="border-2 border-background">
                    <AvatarImage
                      src={`https://api.dicebear.com/7.x/${style}/svg?seed=${seed}`}
                      alt={`User ${i + 1}`}
                    />
                    <AvatarFallback className="text-xs">
                      {seed.substring(0, 2).toUpperCase()}
                    </AvatarFallback>
                  </Avatar>
                );
              })
            ) : (
              // Fallback message when no users yet
              <div className="text-sm text-muted-foreground">
                🎵 Be the first!
              </div>
            )}
          </div>
          <div className="text-left">
            <p className="text-sm font-medium">
              {loading ? (
                <span className="inline-block w-32 h-4 bg-muted animate-pulse rounded" />
              ) : (
                getPlaylistsText()
              )}
            </p>
            <p className="text-xs text-muted-foreground">
              {loading ? (
                <span className="inline-block w-24 h-3 bg-muted animate-pulse rounded mt-1" />
              ) : stats && stats.total_users > 0 ? (
                `Join ${formatNumber(stats.total_users)} music lovers`
              ) : (
                'Join the community'
              )}
            </p>
          </div>
        </motion.div>
      </div>
    </div>
  );
}