/**
 * Input Bar Component
 *
 * Message input with send button and keyboard shortcuts.
 */

'use client';

import { useState, useRef, KeyboardEvent } from 'react';
import { Button } from '../shared/Button';

interface InputBarProps {
  onSend: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
  className?: string;
}

export function InputBar({
  onSend,
  disabled = false,
  placeholder = 'Ask anything...',
  className = '',
}: InputBarProps) {
  const [input, setInput] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = () => {
    if (!input.trim() || disabled) return;

    onSend(input);
    setInput('');

    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);

    // Auto-resize textarea
    e.target.style.height = 'auto';
    e.target.style.height = `${Math.min(e.target.scrollHeight, 200)}px`;
  };

  return (
    <div
      className={`border-t border-aether-indigo-light bg-aether-bg-card p-4 ${className}`}
    >
      <div className="max-w-4xl mx-auto">
        <div className="flex items-end gap-3">
          {/* Textarea */}
          <div className="flex-1 relative">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={handleInput}
              onKeyDown={handleKeyDown}
              placeholder={placeholder}
              disabled={disabled}
              rows={1}
              className="w-full bg-aether-bg-dark border border-aether-indigo-light rounded-2xl px-4 py-3 text-aether-text placeholder-aether-text-muted resize-none focus:outline-none focus:ring-2 focus:ring-aether-purple-light transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              style={{ minHeight: '52px', maxHeight: '200px' }}
            />

            {/* Character counter */}
            <div className="absolute bottom-2 right-3 text-xs text-aether-text-muted">
              {input.length}
            </div>
          </div>

          {/* Send button */}
          <Button
            onClick={handleSend}
            disabled={disabled || !input.trim()}
            variant="primary"
            size="lg"
            className="shrink-0"
          >
            {disabled ? (
              <span className="flex items-center gap-2">
                <svg
                  className="animate-spin h-5 w-5"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  />
                </svg>
                Sending
              </span>
            ) : (
              <span className="flex items-center gap-2">
                <svg
                  width="20"
                  height="20"
                  viewBox="0 0 20 20"
                  fill="none"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path
                    d="M18 2L9 11M18 2L12 18L9 11M18 2L2 8L9 11"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
                Send
              </span>
            )}
          </Button>
        </div>

        {/* Hint text */}
        <p className="mt-2 text-xs text-aether-text-muted text-center">
          Press <kbd className="px-1.5 py-0.5 bg-aether-bg-dark rounded border border-aether-indigo-light">Enter</kbd> to send,{' '}
          <kbd className="px-1.5 py-0.5 bg-aether-bg-dark rounded border border-aether-indigo-light">Shift + Enter</kbd> for new line
        </p>
      </div>
    </div>
  );
}
