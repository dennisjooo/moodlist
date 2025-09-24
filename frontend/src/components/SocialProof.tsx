import { motion, useInView } from 'framer-motion';
import { useRef } from 'react';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';

export default function SocialProof() {
  const containerRef = useRef(null);
  const isInView = useInView(containerRef, { once: true, margin: "-100px" });

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
            {[1, 2, 3, 4, 5].map((i) => (
              <Avatar key={i} className="border-2 border-background">
                <AvatarFallback className="text-xs">U{i}</AvatarFallback>
              </Avatar>
            ))}
          </div>
          <div className="text-left">
            <p className="text-sm font-medium">1,000+ playlists created</p>
            <p className="text-xs text-muted-foreground">Join the community</p>
          </div>
        </motion.div>
      </div>
    </div>
  );
}