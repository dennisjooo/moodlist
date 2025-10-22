import { ThemeProvider } from '@/components/ThemeProvider';
import { Toaster } from '@/components/ui/sonner';
import { AuthProvider } from '@/lib/contexts/AuthContext';
import { WorkflowProvider } from '@/lib/contexts/WorkflowContext';
import { ErrorBoundary } from '@/components/shared';
import { SkipLink } from '@/components/shared/SkipLink';
import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'MoodList - Turn your mood into music',
  description: 'Generate Spotify playlists that match your mood. Describe how you\'re feeling and get the perfect playlist instantly.',
  keywords: ['spotify', 'playlist', 'mood', 'music', 'generator'],
  openGraph: {
    title: 'MoodList - Turn your mood into music',
    description: 'Generate Spotify playlists that match your mood',
    type: 'website',
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={inter.className} suppressHydrationWarning>
        <SkipLink targetId="main-content">Skip to main content</SkipLink>
        <ErrorBoundary>
          <ThemeProvider>
            <AuthProvider>
              <WorkflowProvider>
                <Toaster />
                <div id="main-content" tabIndex={-1}>
                  {children}
                </div>
                {/* ARIA live region for screen reader announcements */}
                <div
                  id="a11y-live-region"
                  role="status"
                  aria-live="polite"
                  aria-atomic="true"
                  className="sr-only"
                />
              </WorkflowProvider>
            </AuthProvider>
          </ThemeProvider>
        </ErrorBoundary>
      </body>
    </html>
  );
}
