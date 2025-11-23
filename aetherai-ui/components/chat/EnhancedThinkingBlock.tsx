'use client';

import { useState, useEffect } from 'react';
import { ChevronDown, ChevronRight, Brain, Zap } from 'lucide-react';

interface ThinkingStep {
  id: number;
  content: string;
  timestamp: number;
  type: 'analysis' | 'calculation' | 'reasoning' | 'conclusion';
}

interface EnhancedThinkingBlockProps {
  rawContent: string;
  isStreaming?: boolean;
  tokenBudget?: number;
  className?: string;
}

export function EnhancedThinkingBlock({
  rawContent,
  isStreaming = false,
  tokenBudget = 512,
  className = ''
}: EnhancedThinkingBlockProps) {
  const [viewMode, setViewMode] = useState<'collapsed' | 'timeline' | 'detailed'>('collapsed');
  const [steps, setSteps] = useState<ThinkingStep[]>([]);
  const [tokensUsed, setTokensUsed] = useState(0);

  // Parse raw thinking into structured steps
  useEffect(() => {
    if (!rawContent) return;

    const lines = rawContent.split('\n').filter(l => l.trim());
    const parsedSteps: ThinkingStep[] = [];

    lines.forEach((line, idx) => {
      // Detect step patterns: "Step X:", numbered lists, bullet points
      const isStep = /^(?:Step \d+:|[-•]\s|\d+\.\s|Next:|Therefore:|Thus:)/i.test(line);

      if (isStep || parsedSteps.length === 0) {
        parsedSteps.push({
          id: idx,
          content: line.replace(/^(?:Step \d+:|[-•]\s|\d+\.\s|Next:|Therefore:|Thus:)/i, '').trim(),
          timestamp: Date.now() + idx * 100,
          type: detectStepType(line),
        });
      } else {
        // Append to last step if continuation
        if (parsedSteps.length > 0) {
          const last = parsedSteps[parsedSteps.length - 1];
          last.content += ' ' + line;
        }
      }
    });

    setSteps(parsedSteps);
    setTokensUsed(Math.ceil(rawContent.split(/\s+/).length * 1.3));
  }, [rawContent]);

  // Detect step type for styling
  function detectStepType(text: string): ThinkingStep['type'] {
    if (/calc|compute|estimate|flop|memory|measure/i.test(text)) return 'calculation';
    if (/analyze|consider|evaluate|profile|examine/i.test(text)) return 'analysis';
    if (/therefore|thus|so|recommend|conclude/i.test(text)) return 'conclusion';
    return 'reasoning';
  }

  const stepTypeConfig = {
    analysis: { icon: '🔍', color: 'text-blue-400', bg: 'bg-blue-500/10' },
    calculation: { icon: '🧮', color: 'text-purple-400', bg: 'bg-purple-500/10' },
    reasoning: { icon: '💭', color: 'text-amber-400', bg: 'bg-amber-500/10' },
    conclusion: { icon: '✓', color: 'text-green-400', bg: 'bg-green-500/10' },
  };

  if (!rawContent) return null;

  return (
    <div className={`my-4 ${className}`}>
      {/* Collapsed View - Minimal, elegant */}
      {viewMode === 'collapsed' && (
        <button
          onClick={() => setViewMode('timeline')}
          className="group flex items-center gap-3 w-full p-3 rounded-xl bg-gradient-to-r from-aether-purple-dark/50 to-aether-purple-mid/50 border border-aether-purple-light/30 hover:border-aether-orange/50 transition-all"
        >
          <div className="flex items-center gap-2 flex-1">
            <Brain className={`w-4 h-4 ${isStreaming ? 'animate-pulse' : ''} text-aether-purple-light`} />
            <span className="text-sm font-medium text-aether-purple-light">
              {isStreaming ? 'Thinking...' : 'View reasoning process'}
            </span>
            <span className="text-xs text-aether-text-muted">
              {steps.length} {steps.length === 1 ? 'step' : 'steps'} • {tokensUsed}/{tokenBudget} tokens
            </span>
          </div>
          <ChevronRight className="w-4 h-4 text-aether-text-muted group-hover:text-aether-orange transition-colors" />
        </button>
      )}

      {/* Timeline View - Step-by-step */}
      {viewMode === 'timeline' && (
        <div className="border border-aether-purple-light/30 rounded-xl bg-aether-bg-card overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between p-4 border-b border-aether-purple-light/30 bg-gradient-to-r from-aether-purple-dark/30 to-transparent">
            <div className="flex items-center gap-3">
              <Brain className="w-5 h-5 text-aether-purple-light" />
              <div>
                <h4 className="text-sm font-semibold text-aether-text">Reasoning Timeline</h4>
                <p className="text-xs text-aether-text-muted">
                  {tokensUsed} tokens • {steps.length} {steps.length === 1 ? 'step' : 'steps'}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setViewMode('detailed')}
                className="px-3 py-1.5 text-xs bg-aether-purple-dark border border-aether-purple-light rounded-lg hover:bg-aether-purple-mid transition-colors"
              >
                Full Detail
              </button>
              <button
                onClick={() => setViewMode('collapsed')}
                className="p-1.5 hover:bg-aether-bg-hover rounded-lg transition-colors"
              >
                <ChevronDown className="w-4 h-4 text-aether-text" />
              </button>
            </div>
          </div>

          {/* Steps */}
          <div className="p-4 space-y-3 max-h-96 overflow-y-auto">
            {steps.map((step, idx) => {
              const config = stepTypeConfig[step.type];
              return (
                <div
                  key={step.id}
                  className="flex gap-3 animate-fade-in"
                  style={{ animationDelay: `${idx * 50}ms` }}
                >
                  {/* Timeline connector */}
                  <div className="flex flex-col items-center pt-1">
                    <div className={`w-8 h-8 rounded-full ${config.bg} flex items-center justify-center text-sm flex-shrink-0`}>
                      {config.icon}
                    </div>
                    {idx < steps.length - 1 && (
                      <div className="w-0.5 flex-1 bg-gradient-to-b from-aether-purple-light/50 to-transparent mt-2 min-h-[20px]" />
                    )}
                  </div>

                  {/* Step content */}
                  <div className="flex-1 pb-4">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`text-xs font-semibold ${config.color}`}>
                        {step.type.charAt(0).toUpperCase() + step.type.slice(1)}
                      </span>
                      <span className="text-xs text-aether-text-muted">
                        Step {idx + 1}
                      </span>
                    </div>
                    <p className="text-sm text-aether-text leading-relaxed">
                      {step.content}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Token budget indicator */}
          <div className="px-4 pb-4">
            <div className="flex items-center justify-between text-xs text-aether-text-muted mb-1">
              <span>Thinking Budget</span>
              <span>{tokensUsed} / {tokenBudget}</span>
            </div>
            <div className="h-1.5 bg-aether-bg-dark rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-aether-purple-light to-aether-orange transition-all duration-300"
                style={{ width: `${Math.min((tokensUsed / tokenBudget) * 100, 100)}%` }}
              />
            </div>
          </div>
        </div>
      )}

      {/* Detailed View - Full technical breakdown */}
      {viewMode === 'detailed' && (
        <div className="border border-aether-purple-light/30 rounded-xl bg-aether-bg-card overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between p-4 border-b border-aether-purple-light/30">
            <h4 className="text-sm font-semibold text-aether-text">Full Reasoning Trace</h4>
            <button
              onClick={() => setViewMode('timeline')}
              className="text-xs text-aether-purple-light hover:text-aether-orange transition-colors"
            >
              ← Back to Timeline
            </button>
          </div>

          {/* Raw content */}
          <div className="p-4 max-h-96 overflow-y-auto">
            <pre className="text-xs text-aether-text-muted font-mono whitespace-pre-wrap leading-relaxed bg-aether-bg-dark/50 p-4 rounded-lg border border-aether-purple-light/20">
              {rawContent}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}
