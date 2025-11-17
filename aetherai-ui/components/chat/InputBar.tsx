/**
 * Input Bar Component
 *
 * Text input with auto-resize textarea and send button.
 */

'use client';

import { useState, useRef, useEffect, KeyboardEvent } from 'react';
import { useChatStore } from '@/lib/stores/chatStore';
import { streamChat } from '@/lib/api/streaming';
import { Button } from '../shared/Button';

interface InputBarProps {
  className?: string;
}

export function InputBar({ className = '' }: InputBarProps) {
  const [input, setInput] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const {
    messages,
    currentModel,
    isStreaming,
    addMessage,
    updateLastMessage,
    setIsStreaming,
  } = useChatStore();

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }, [input]);

  // Focus textarea on mount
  useEffect(() => {
    textareaRef.current?.focus();
  }, []);

  const handleSend = async () => {
    if (!input.trim() || isStreaming) return;

    const userMessage = input.trim();
    setInput('');

    // Add user message
    addMessage({
      role: 'user',
      content: userMessage,
    });

    // Start streaming
    setIsStreaming(true);

    // Add empty assistant message that we'll update
    addMessage({
      role: 'assistant',
      content: '',
      model: currentModel === 'auto' ? undefined : currentModel,
    });

    try {
      await streamChat(
        {
          messages: [
            ...messages.map((m) => ({
              role: m.role,
              content: m.content,
            })),
            {
              role: 'user',
              content: userMessage,
            },
          ],
          model: currentModel,
        },
        {
          onContent: (content) => {
            updateLastMessage({ content });
          },
          onThinking: (thinking) => {
            updateLastMessage({ thinking });
          },
          onModel: (model) => {
            updateLastMessage({ model });
          },
          onDone: () => {
            setIsStreaming(false);
          },
          onError: (error) => {
            console.error('Streaming error:', error);
            updateLastMessage({
              content: '⚠️ Sorry, there was an error processing your request.',
            });
            setIsStreaming(false);
          },
        }
      );
    } catch (error) {
      console.error('Chat error:', error);
      updateLastMessage({
        content: '⚠️ Failed to connect to the API. Please try again.',
      });
      setIsStreaming(false);
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    // Enter to send, Shift+Enter for newline
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className={`border-t border-aether-indigo-light bg-aether-bg-card p-4 ${className}`}>
      <div className="max-w-4xl mx-auto">
        <div className="flex items-end gap-3">
          {/* Auto-resize textarea */}
          <div className="flex-1 relative">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={
                isStreaming
                  ? 'Waiting for response...'
                  : 'Ask anything... (Shift+Enter for newline)'
              }
              disabled={isStreaming}
              className="w-full resize-none rounded-lg bg-aether-bg-dark border border-aether-indigo-light px-4 py-3 text-aether-text placeholder:text-aether-text-muted focus:outline-none focus:ring-2 focus:ring-aether-purple-light transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              rows={1}
              style={{
                maxHeight: '200px',
                minHeight: '52px',
              }}
            />
          </div>

          {/* Send button */}
          <Button
            onClick={handleSend}
            disabled={!input.trim() || isStreaming}
            variant="primary"
            size="md"
            className="shrink-0"
          >
            {isStreaming ? (
              <span className="flex items-center gap-2">
                <div className="flex gap-1">
                  <span className="animate-pulse">●</span>
                  <span className="animate-pulse" style={{ animationDelay: '0.2s' }}>
                    ●
                  </span>
                  <span className="animate-pulse" style={{ animationDelay: '0.4s' }}>
                    ●
                  </span>
                </div>
              </span>
            ) : (
              <span className="flex items-center gap-2">
                Send
                <svg
                  width="16"
                  height="16"
                  viewBox="0 0 16 16"
                  fill="none"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path
                    d="M15 1L7 9M15 1L10 15L7 9M15 1L1 6L7 9"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </span>
            )}
          </Button>
        </div>

        {/* Model indicator */}
        <div className="mt-2 text-xs text-aether-text-muted flex items-center gap-2">
          <span>Model:</span>
          <span className="text-aether-purple-light font-semibold">
            {currentModel === 'auto' ? 'Auto-Select' : currentModel.charAt(0).toUpperCase() + currentModel.slice(1)}
          </span>
        </div>
      </div>
    </div>
  );
}
