'use client';

import dynamic from 'next/dynamic';

const ChatInterface = dynamic(
  () => import('@/components/chat/ChatInterface'),
  {
    ssr: false,
    loading: () => (
      <div className="flex items-center justify-center min-h-screen bg-aether-bg-dark">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-aether-purple-light mx-auto mb-4" />
          <p className="text-aether-text-muted">Initializing AetherAI...</p>
        </div>
      </div>
    ),
  }
);

export default function HomePage() {
  return <ChatInterface />;
}
