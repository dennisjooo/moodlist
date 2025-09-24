'use client';

import { useEffect } from 'react';
import Typewriter from 'typewriter-effect';

interface TypewriterTextProps {
  strings: string[];
  className?: string;
}

export default function TypewriterText({ strings, className = '' }: TypewriterTextProps) {
  return (
    <div className={className}>
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