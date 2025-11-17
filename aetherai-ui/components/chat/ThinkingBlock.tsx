/**
 * Thinking Block Component
 *
 * Displays AI reasoning process (collapsible).
 * Shows transparency in decision-making.
 */

'use client';

import { useState } from 'react';

interface ThinkingBlockProps {
  content: string;
  className?: string;
}

export function ThinkingBlock({ content, className = '' }: ThinkingBlockProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!content) return null;

  return (
    <div className={`my-2 ${className}`}>
      {/* Toggle button */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center gap-2 text-sm text-aether-purple-light hover:text-aether-purple-dark transition-colors mb-2"
      >
        <span className="transform transition-transform duration-200">
          {isExpanded ? '↓' : '→'}
        </span>
        <span className="font-medium">
          {isExpanded ? 'Hide' : 'Show'} reasoning
        </span>
        <span className="text-aether-text-muted">({content.length} chars)</span>
      </button>

      {/* Thinking content */}
      {isExpanded && (
        <div className="border-l-4 border-aether-purple-light bg-aether-bg-card rounded-r-lg p-4 animate-slide-up">
          <div className="flex items-start gap-2 mb-2">
            <span className="text-lg">🧠</span>
            <span className="text-sm font-semibold text-aether-purple-light">
              Model Reasoning
            </span>
          </div>
          <pre className="text-sm text-aether-text-muted font-mono whitespace-pre-wrap break-words">
            {content}
          </pre>
        </div>
      )}
    </div>
  );
}
