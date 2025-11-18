/**
 * Home Page
 *
 * Main chat interface page.
 */

import dynamic from 'next/dynamic';

// Dynamically import ChatInterface with no SSR to prevent hydration issues
const ChatInterface = dynamic(
  () => import('@/components/chat/ChatInterface').then(mod => ({ default: mod.ChatInterface })),
  {
    ssr: false,
    loading: () => <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-purple-900 via-slate-900 to-black"><div className="text-6xl animate-pulse">⚡</div></div>
  }
);

export default function HomePage() {
  return <ChatInterface />;
}
