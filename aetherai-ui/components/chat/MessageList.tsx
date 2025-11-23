/**
 * Message List Component
 *
 * Scrollable container for messages with auto-scroll.
 */

'use client';

import { useEffect, useRef } from 'react';
import { Message as MessageType } from '@/lib/stores/chatStore';
import { Message } from './Message';
import { LogoWithTagline } from '../shared/Logo';
import { ToolUseIndicator } from './ToolUseIndicator';

interface MessageListProps {
  messages: MessageType[];
  isStreaming?: boolean;
  currentToolUse?: { tool: string; query: string; results?: any[]; isSearching: boolean } | null;
  className?: string;
}

export function MessageList({
  messages,
  isStreaming = false,
  currentToolUse = null,
  className = '',
}: MessageListProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isStreaming]);

  // Empty state
  if (messages.length === 0) {
    return (
      <div
        ref={containerRef}
        className={`flex-1 overflow-y-auto p-6 flex items-center justify-center ${className}`}
      >
        <div className="text-center max-w-2xl">
          <LogoWithTagline />
          <div className="mt-8 space-y-4">
            <h2 className="text-2xl font-semibold text-aether-text">
              Start a conversation
            </h2>
            <p className="text-aether-text-muted">
              Choose your model, ask anything. Your data stays on US soil.
            </p>

            {/* Example prompts */}
            <div className="mt-8 grid gap-3">
              <div className="bg-aether-bg-card border border-aether-indigo-light rounded-lg p-4 text-left hover:bg-aether-bg-hover transition-colors cursor-pointer">
                <p className="text-sm text-aether-text">
                  💡 Explain async/await in Python
                </p>
              </div>
              <div className="bg-aether-bg-card border border-aether-indigo-light rounded-lg p-4 text-left hover:bg-aether-bg-hover transition-colors cursor-pointer">
                <p className="text-sm text-aether-text">
                  🔍 Analyze this code for security issues
                </p>
              </div>
              <div className="bg-aether-bg-card border border-aether-indigo-light rounded-lg p-4 text-left hover:bg-aether-bg-hover transition-colors cursor-pointer">
                <p className="text-sm text-aether-text">
                  🚀 Design a microservices architecture
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Messages list
  return (
    <div
      ref={containerRef}
      className={`flex-1 overflow-y-auto p-6 ${className}`}
    >
      <div className="max-w-4xl mx-auto">
        {messages.map((message) => (
          <Message key={message.id} message={message} />
        ))}

        {/* Tool use indicator - only during streaming */}
        {isStreaming && currentToolUse && (
          <ToolUseIndicator
            tool={currentToolUse.tool}
            query={currentToolUse.query}
            results={currentToolUse.results}
            isSearching={currentToolUse.isSearching}
          />
        )}

        {/* Streaming indicator */}
        {isStreaming && !currentToolUse && (
          <div className="flex items-center gap-2 text-aether-purple-light mb-4">
            <div className="flex gap-1">
              <span className="animate-pulse">●</span>
              <span className="animate-pulse" style={{ animationDelay: '0.2s' }}>
                ●
              </span>
              <span className="animate-pulse" style={{ animationDelay: '0.4s' }}>
                ●
              </span>
            </div>
            <span className="text-sm animate-thinking">Thinking...</span>
          </div>
        )}

        {/* Scroll anchor */}
        <div ref={messagesEndRef} />
      </div>
    </div>
  );
}
