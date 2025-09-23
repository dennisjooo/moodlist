'use client';

import { useEffect, useRef } from 'react';
import Typewriter from 'typewriter-effect';

interface TypewriterTextProps {
  strings: string[];
  className?: string;
}

export default function TypewriterText({ strings, className = '' }: TypewriterTextProps) {
  const typewriterRef = useRef<HTMLDivElement>(null);

  return (
    <div ref={typewriterRef} className={className}>
      <Typewriter
        options={{
          strings: strings,
          autoStart: true,
          loop: true,
          delay: 75,
          deleteSpeed: 50,
          cursor: '|',
        }}
      />
    </div>
  );
}