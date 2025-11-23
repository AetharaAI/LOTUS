/**
 * Message Component
 *
 * Individual message bubble with markdown support.
 */

'use client';

import { Message as MessageType } from '@/lib/stores/chatStore';
import { MarkdownRenderer } from '../shared/MarkdownRenderer';
import { ThinkingBlock } from './ThinkingBlock';
import { ModelBadge } from '../shared/ModelBadge';

interface MessageProps {
  message: MessageType;
  className?: string;
}

export function Message({ message, className = '' }: MessageProps) {
  const isUser = message.role === 'user';

  return (
    <div className={`mb-6 ${className}`}>
      <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
        <div className={`max-w-[85%] ${isUser ? 'order-2' : 'order-1'}`}>
          {/* Header with role and model badge */}
          <div className="flex items-center gap-2 mb-2">
            {!isUser && (
              <>
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-aether-purple-light to-aether-indigo-light flex items-center justify-center">
                  <span className="text-white text-sm font-bold">A</span>
                </div>
                <span className="text-sm font-semibold text-aether-text">
                  Apriel
                </span>
                {message.model && <ModelBadge model={message.model} />}
              </>
            )}
            {isUser && (
              <span className="text-sm font-semibold text-aether-text-muted">
                You
              </span>
            )}
          </div>

          {/* Thinking block (only for assistant) */}
          {!isUser && message.thinking && (
            <ThinkingBlock content={message.thinking} className="mb-3" />
          )}

          {/* Message content */}
          <div
            className={`rounded-2xl px-4 py-3 ${
              isUser
                ? 'bg-gradient-to-r from-aether-purple-dark to-aether-purple-light text-white'
                : 'bg-aether-bg-card border border-aether-indigo-light text-aether-text'
            }`}
          >
            {isUser ? (
              <p className="whitespace-pre-wrap break-words">{message.content}</p>
            ) : (
              <MarkdownRenderer content={message.content} />
            )}
          </div>

          {/* Timestamp */}
          <div className="mt-1 text-xs text-aether-text-muted">
            {new Date(message.timestamp).toLocaleTimeString()}
          </div>
        </div>
      </div>
    </div>
  );
}
