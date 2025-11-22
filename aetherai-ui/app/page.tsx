'use client';

import dynamic from 'next/dynamic';

// We use ssr: false because 'react-draggable' uses window/document, 
// which doesn't exist on the server.
const ChatInterface = dynamic(
  () => import('@/components/chat/ChatInterface'), 
  { 
    ssr: false,
    loading: () => <div className="fixed bottom-10 right-10 text-slate-500">Initializing L40S Link...</div>
  }
);

export default function HomePage() {
  return (
    <main className="relative min-h-screen bg-slate-950">
      {/* Your Background or Dashboard content goes here */}
      <div className="p-10 text-slate-700">
        <h1 className="text-4xl font-bold opacity-20">AETHERPRO // SOVEREIGN NODE</h1>
      </div>

      {/* The Floating Pendant */}
      <ChatInterface />
    </main>
  );
}