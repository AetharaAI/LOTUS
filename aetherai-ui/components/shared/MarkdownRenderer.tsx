/**
 * Markdown Renderer
 *
 * Renders markdown with syntax highlighting for code blocks.
 */

'use client';

import React, { useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

export function MarkdownRenderer({
  content,
  className = '',
}: MarkdownRendererProps) {
  useEffect(() => {
    // Load Prism.js for syntax highlighting
    if (typeof window !== 'undefined') {
      import('prismjs').then(async (Prism) => {
        // Import common languages
        await Promise.all([
          import('prismjs/components/prism-javascript'),
          import('prismjs/components/prism-typescript'),
          import('prismjs/components/prism-python'),
          import('prismjs/components/prism-bash'),
          import('prismjs/components/prism-json'),
          import('prismjs/components/prism-yaml'),
          import('prismjs/components/prism-markdown'),
        ]);

        // Highlight all code blocks
        Prism.default.highlightAll();
      });
    }
  }, [content]);

  return (
    <div className={`prose prose-invert max-w-none ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          code({ className, children, ...props }: any) {
            const match = /language-(\w+)/.exec(className || '');
            const language = match ? match[1] : '';

            // Check if it's inline code (no language specified and single line)
            const isInline = !className && typeof children === 'string' && !children.includes('\n');

            if (isInline) {
              // Inline code
              return (
                <code className="bg-aether-bg-dark px-1 py-0.5 rounded text-aether-purple-light" {...props}>
                  {children}
                </code>
              );
            }

            // Code block
            return (
              <div className="relative group">
                {language && (
                  <div className="absolute top-2 right-2 text-xs text-aether-text-muted bg-aether-bg-card px-2 py-1 rounded">
                    {language}
                  </div>
                )}
                <pre className={`language-${language}`}>
                  <code className={`language-${language}`} {...props}>
                    {children}
                  </code>
                </pre>
              </div>
            );
          },
          a({ href, children }) {
            return (
              <a
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                className="text-aether-purple-light hover:text-aether-purple-dark underline"
              >
                {children}
              </a>
            );
          },
          ul({ children }) {
            return (
              <ul className="list-disc list-inside space-y-1 my-2">
                {children}
              </ul>
            );
          },
          ol({ children }) {
            return (
              <ol className="list-decimal list-inside space-y-1 my-2">
                {children}
              </ol>
            );
          },
          blockquote({ children }) {
            return (
              <blockquote className="border-l-4 border-aether-purple-light pl-4 italic text-aether-text-muted my-2">
                {children}
              </blockquote>
            );
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
