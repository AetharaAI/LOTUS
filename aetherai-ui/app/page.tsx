/**
 * Home Page
 *
 * Main chat interface page.
 * Uses dynamic import to prevent SSR hydration issues with Zustand.
 */

'use client';

import dynamic from 'next/dynamic';

// Dynamically import ChatInterface with no SSR
// This prevents hydration mismatches with Zustand store
const ChatInterface = dynamic(
  () => import('@/components/chat/ChatInterface').then(mod => ({ default: mod.ChatInterface })),
  {
    ssr: false,
    loading: () => (
      <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-purple-900 via-slate-900 to-black">
        <div className="text-center">
          <div className="animate-pulse mb-4">
            <div className="text-6xl">⚡</div>
          </div>
          <p className="text-purple-300">Loading AetherAI...</p>
        </div>
      </div>
    )
  }
);

export default function HomePage() {
  return <ChatInterface />;
}
