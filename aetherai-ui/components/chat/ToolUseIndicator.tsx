'use client';

import { Search, ExternalLink, Loader2 } from 'lucide-react';

interface SearchResult {
  position: number;
  title: string;
  url: string;
  snippet: string;
  engine: string;
}

interface ToolUseIndicatorProps {
  tool: string;
  query: string;
  results?: SearchResult[];
  isSearching?: boolean;
  className?: string;
}

export function ToolUseIndicator({
  tool,
  query,
  results,
  isSearching = false,
  className = ''
}: ToolUseIndicatorProps) {
  if (tool !== 'web_search') return null;

  return (
    <div className={`my-3 p-4 rounded-lg border border-aether-orange/30 bg-aether-orange/5 ${className}`}>
      <div className="flex items-center gap-2 mb-2">
        {isSearching ? (
          <Loader2 className="w-4 h-4 text-aether-orange animate-spin" />
        ) : (
          <Search className="w-4 h-4 text-aether-orange" />
        )}
        <span className="text-sm font-medium text-aether-orange">
          {isSearching ? 'Searching the web...' : 'Web search completed'}
        </span>
      </div>

      <p className="text-xs text-aether-text-muted mb-3">
        Query: <span className="font-mono text-aether-text">"{query}"</span>
      </p>

      {results && results.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-medium text-aether-text">
            Found {results.length} {results.length === 1 ? 'source' : 'sources'}:
          </p>
          <div className="space-y-1.5">
            {results.slice(0, 3).map((result, idx) => (
              <a
                key={idx}
                href={result.url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-start gap-2 text-xs text-aether-purple-light hover:text-aether-orange transition-colors group p-2 rounded hover:bg-aether-bg-dark/50"
              >
                <ExternalLink className="w-3 h-3 mt-0.5 opacity-50 group-hover:opacity-100 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="font-medium line-clamp-1">{result.title}</div>
                  {result.snippet && (
                    <div className="text-aether-text-muted line-clamp-2 mt-0.5">
                      {result.snippet}
                    </div>
                  )}
                </div>
              </a>
            ))}
          </div>
        </div>
      )}

      {results && results.length === 0 && !isSearching && (
        <p className="text-xs text-aether-text-muted italic">
          No results found
        </p>
      )}
    </div>
  );
}
