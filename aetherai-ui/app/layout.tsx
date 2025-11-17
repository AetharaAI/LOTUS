/**
 * Root Layout
 *
 * Next.js 14 App Router root layout with metadata and global styles.
 * Note: Fonts are loaded via Google Fonts CDN in globals.css
 */

import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'AetherAI - The American Standard for Sovereign AI Infrastructure',
  description:
    'A sovereign, model-agnostic AI platform built on US infrastructure. Chat with Apriel, Grok-2, and Claude - your data stays on US soil.',
  keywords: [
    'AI',
    'sovereign AI',
    'US infrastructure',
    'Apriel',
    'Grok-2',
    'Claude',
    'chat',
    'artificial intelligence',
  ],
  authors: [{ name: 'AetherAI' }],
  openGraph: {
    title: 'AetherAI',
    description: 'The American Standard for Sovereign AI Infrastructure',
    type: 'website',
  },
  icons: {
    icon: '/favicon.ico',
  },
  viewport: {
    width: 'device-width',
    initialScale: 1,
  },
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
