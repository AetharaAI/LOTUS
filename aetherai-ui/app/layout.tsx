/**
 * Root Layout
 *
 * Next.js 14 App Router root layout with metadata and global styles.
 * Note: Fonts are loaded via Google Fonts CDN in globals.css
 */

import type { Metadata, Viewport } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'AetherAI - Sovereign AI Platform',
  description: 'The American Standard for Sovereign AI. Powered by Apriel on US infrastructure.',
  keywords: [
    'AI',
    'sovereign AI',
    'US infrastructure',
    'Apriel',
    'chat',
    'artificial intelligence',
  ],
  authors: [{ name: 'AetherAI' }],
  openGraph: {
    title: 'AetherAI',
    description: 'The American Standard for Sovereign AI',
    type: 'website',
  },
  icons: {
    icon: [
      { url: '/favicon-16x16.png', sizes: '16x16', type: 'image/png' },
      { url: '/favicon-32x32.png', sizes: '32x32', type: 'image/png' },
      { url: '/favicon-48x48.png', sizes: '48x48', type: 'image/png' },
    ],
    apple: '/apple-touch-icon.png',
    other: [
      { rel: 'icon', url: '/favicon.ico' },
    ],
  },
  manifest: '/site.webmanifest',
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="font-sans antialiased">
        {children}
      </body>
    </html>
  );
}
