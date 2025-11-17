/**
 * Message Component
 *
 * Individual message bubble (user or assistant).
 */

'use client';

import { useState } from 'react';
import { Message as MessageType } from '@/lib/stores/chatStore';
import { MarkdownRenderer } from '../shared/MarkdownRenderer';
import { ModelBadge } from '../shared/ModelBadge';
import { ThinkingBlock } from './ThinkingBlock';

interface MessageProps {
  message: MessageType;
  className?: string;
}

export function Message({ message, className = '' }: MessageProps) {
  const [showCopyButton, setShowCopyButton] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const formatTime = (date: Date) => {
    return new Date(date).toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
    });
  };

  if (message.role === 'user') {
    // User message - purple gradient bubble (right-aligned)
    return (
      <div className={`flex justify-end mb-4 animate-slide-up ${className}`}>
        <div className="max-w-[80%]">
          <div className="message-user text-white rounded-2xl px-4 py-3 shadow-lg">
            <div className="whitespace-pre-wrap break-words">{message.content}</div>
          </div>
          <div className="text-xs text-aether-text-muted text-right mt-1">
            {formatTime(message.timestamp)}
          </div>
        </div>
      </div>
    );
  }

  // Assistant message - dark card with gradient border (left-aligned)
  return (
    <div
      className={`flex justify-start mb-4 animate-slide-up ${className}`}
      onMouseEnter={() => setShowCopyButton(true)}
      onMouseLeave={() => setShowCopyButton(false)}
    >
      <div className="max-w-[85%]">
        {/* Model badge */}
        {message.model && (
          <div className="mb-2">
            <ModelBadge model={message.model} />
          </div>
        )}

        {/* Thinking block (if present) */}
        {message.thinking && <ThinkingBlock content={message.thinking} />}

        {/* Message content */}
        <div className="message-assistant rounded-2xl px-4 py-3 shadow-lg relative">
          {/* Copy button */}
          {showCopyButton && (
            <button
              onClick={handleCopy}
              className="absolute top-2 right-2 bg-aether-bg-dark text-aether-text-muted hover:text-aether-purple-light px-2 py-1 rounded text-xs transition-colors"
              title="Copy to clipboard"
            >
              {copied ? '✓ Copied' : '📋 Copy'}
            </button>
          )}

          <MarkdownRenderer content={message.content} />
        </div>

        {/* Timestamp */}
        <div className="text-xs text-aether-text-muted mt-1 flex items-center gap-2">
          <span>{formatTime(message.timestamp)}</span>
          {message.model && (
            <>
              <span>•</span>
              <span className="capitalize">{message.model}</span>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
