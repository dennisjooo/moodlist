import { ThemeProvider } from '@/components/ThemeProvider';
import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'MoodList - Turn your mood into music',
  description: 'Generate Spotify playlists that match your mood. Describe how you\'re feeling and get the perfect playlist instantly.',
  keywords: ['spotify', 'playlist', 'mood', 'music', 'generator'],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={inter.className} suppressHydrationWarning>
        <ThemeProvider>
          {children}
        </ThemeProvider>
      </body>
    </html>
  );
}
