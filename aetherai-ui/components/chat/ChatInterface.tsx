/**
 * Chat Interface Component
 *
 * Main container that combines Sidebar, MessageList, and InputBar.
 */

'use client';

import { useState } from 'react';
import { useChatStore } from '@/lib/stores/chatStore';
import { Sidebar } from './Sidebar';
import { MessageList } from './MessageList';
import { InputBar } from './InputBar';
import { Logo } from '../shared/Logo';

export function ChatInterface() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const { messages, isStreaming } = useChatStore();

  return (
    <div className="flex h-screen bg-aether-bg-dark">
      {/* Sidebar - Desktop */}
      <div className="hidden md:block w-64 shrink-0">
        <Sidebar />
      </div>

      {/* Sidebar - Mobile (Overlay) */}
      {isSidebarOpen && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 bg-black/50 z-40 md:hidden"
            onClick={() => setIsSidebarOpen(false)}
          />

          {/* Sidebar */}
          <div className="fixed inset-y-0 left-0 w-64 z-50 md:hidden animate-slide-in">
            <Sidebar onClose={() => setIsSidebarOpen(false)} />
          </div>
        </>
      )}

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <header className="shrink-0 bg-aether-bg-card border-b border-aether-indigo-light px-4 py-3">
          <div className="flex items-center justify-between max-w-4xl mx-auto">
            {/* Mobile menu button */}
            <button
              onClick={() => setIsSidebarOpen(true)}
              className="md:hidden p-2 text-aether-text-muted hover:text-aether-text transition-colors"
            >
              <svg
                width="24"
                height="24"
                viewBox="0 0 24 24"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
              >
                <path
                  d="M3 12H21M3 6H21M3 18H21"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </button>

            {/* Logo */}
            <div className="flex-1 flex justify-center md:justify-start">
              <Logo size="sm" />
            </div>

            {/* Spacer for mobile centering */}
            <div className="md:hidden w-10" />
          </div>
        </header>

        {/* Messages */}
        <MessageList messages={messages} isStreaming={isStreaming} />

        {/* Input Bar */}
        <InputBar />
      </div>
    </div>
  );
}
