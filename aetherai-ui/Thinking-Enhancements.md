


# 🚀 GENERATING: AetherAI Enhancement Specification v1.0

**This will include:**

## Phase 9: Response Quality & Brevity
- Updated system prompt (concise, professional)
- Tuned model parameters (reduced verbosity)
- Response length limiters

## Phase 10: Enterprise Thinking Display
- `EnhancedThinkingBlock.tsx` component (3 view modes)
- Timeline view with step detection
- Token budget visualization
- Animated step transitions
- Updated `Message.tsx` integration

## Phase 11: Sovereign Web Search
- `/api/search/route.ts` (SearXNG integration)
- Tool calling support in chat completions
- `ToolUseIndicator.tsx` component
- Search result display
- Citation handling

## Phase 6.3-6.4 (from earlier)
- Tailwind color palette update (deep purple)
- Logo asset integration
- Favicon setup

## Additional Polish
- CSS animations
- Loading states
- Error handling
- Environment variable updates

---

**Creating the spec now...**

<invoke name="create_file">
<parameter name="description">Creating the complete AetherAI Enhancement Specification v1.0 for Claude Code to execute. This is a comprehensive, step-by-step guide with all code, no ambiguity.</parameter>
<parameter name="path">/mnt/user-data/outputs/AETHERAI-ENHANCEMENT-SPEC-V1.md</parameter>
<parameter name="file_text"># AetherAI Enhancement Specification v1.0

**Project:** AetherAI Production Enhancement
**Target:** Enterprise-grade thinking display + sovereign web search + response quality tuning
**Executor:** Claude Code
**Timeline:** Single deployment cycle
**Status:** Ready for execution

---

## 🎯 OBJECTIVES

1. **Response Quality:** Reduce verbosity, improve conciseness (60% reduction in token usage)
2. **Thinking Display:** World-class 3-tier reasoning visualization (Timeline/Detailed/Collapsed)
3. **Web Search:** Sovereign search integration via SearXNG (zero external dependencies)
4. **Brand Polish:** Deep purple color scheme + logo integration
5. **Production Ready:** Error handling, loading states, animations

---

## 📋 PREREQUISITES

**Verify before starting:**
- ✅ SearXNG running at `http://localhost:8888` (test: `curl http://localhost:8888/search?q=test&format=json`)
- ✅ vLLM Apriel endpoint at `https://api.aetherpro.tech/v1/chat/completions`
- ✅ Logo files in `~/Pictures/AetherAI-Branding-&-Logo/favicon/`
- ✅ Current working directory: `~/path/to/aetherai-ui` (Next.js project root)

---

## ✅ PHASE 9: RESPONSE QUALITY TUNING

### Task 9.1: Update System Prompt for Conciseness

**File:** `app/api/chat/completions/route.ts`

**Action:** Replace the `SYSTEM_PROMPT` constant (around line 3-10)

**Find:**
```typescript
const SYSTEM_PROMPT = `
You are Apriel, Sovereign AI of AetherPro.
ROLE: Enterprise Architect for Sovereign AI.
TONE: Professional, Astute, Concise.
INSTRUCTION: Provide assistance to Sovereign AI Enterprise and answer general inquiries to any questions including non-domain topics.
`;
```

**Replace with:**
```typescript
const SYSTEM_PROMPT = `You are Apriel, Sovereign AI of AetherPro Technologies.

CRITICAL RESPONSE RULES:
- Maximum 300 words per response (unless user explicitly requests more detail)
- Lead with direct answer in 1-2 sentences
- Use 2-3 bullet points maximum for key details
- NO tables, charts, or extensive formatting by default
- Be conversational, not academic

ROLE: Technical advisor and AI architect for sovereign infrastructure

TONE: Professional senior engineer giving a quick briefing

TOOL USAGE:
- You have access to web_search for current information
- Use ONLY when query requires recent data or facts beyond your training
- Always cite sources when using search results

RESPONSE STRUCTURE:
1. Direct answer (1-2 sentences)
2. Key supporting points (2-3 bullets if needed)
3. Offer to elaborate: "Need more detail on anything?"

GOOD EXAMPLE:
"You'd need an RTX 3060 Ti minimum (8GB VRAM) for that pipeline. Gives you ~15 TFLOPs which handles vision + audio + voice at 1080p/30fps. Want specifics on any component?"

BAD EXAMPLE:
[Long tables, extensive calculations, multiple sections, step-by-step breakdowns without being asked]

When thinking through complex problems:
- Break reasoning into clear steps (use "Step 1:", "Next:", "Therefore:")
- Keep each thinking step to 1-2 sentences
- Conclude thinking before providing final answer`;
```

---

### Task 9.2: Tune Model Parameters

**File:** `app/api/chat/completions/route.ts`

**Action:** Update the `fetch` body in the `POST` function (around line 25-40)

**Find:**
```typescript
body: JSON.stringify({
  model: model || 'apriel-1.5-15b-thinker',
  messages: fullMessages,
  temperature: 0.6,
  repetition_penalty: 1.1,
  max_tokens: 4096,
  stream: true,
}),
```

**Replace with:**
```typescript
body: JSON.stringify({
  model: model || 'apriel-1.5-15b-thinker',
  messages: fullMessages,
  temperature: 0.7,
  repetition_penalty: 1.25,      // Increased to kill "We can also mention" loops
  max_tokens: 600,                // Reduced to force brevity (~450 words)
  top_p: 0.92,                    // Added to reduce unlikely tokens
  frequency_penalty: 0.2,         // Penalizes word repetition
  presence_penalty: 0.1,          // Encourages topic diversity
  stream: true,
  tools: TOOLS,                   // Will define in Phase 11
  tool_choice: 'auto',            // Let model decide when to search
}),
```

**Why these parameters:**
- `repetition_penalty: 1.25` - Strongly discourages repetitive patterns
- `max_tokens: 600` - Hard limit forces concise responses
- `top_p: 0.92` - Reduces sampling of unlikely continuations
- `frequency_penalty: 0.2` - Penalizes repeating words within response
- `presence_penalty: 0.1` - Encourages staying on topic

---

## ✅ PHASE 10: ENTERPRISE THINKING DISPLAY

### Task 10.1: Create EnhancedThinkingBlock Component

**File:** `components/chat/EnhancedThinkingBlock.tsx` (NEW FILE)

**Action:** Create this file with the following content:

```typescript
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
```

---

### Task 10.2: Update Message Component

**File:** `components/chat/Message.tsx`

**Action:** Replace the thinking block import and usage

**Find:**
```typescript
import { ThinkingBlock } from './ThinkingBlock';
```

**Replace with:**
```typescript
import { EnhancedThinkingBlock } from './EnhancedThinkingBlock';
```

**Find (around line 40-45):**
```typescript
{!isUser && message.thinking && (
  <ThinkingBlock content={message.thinking} className="mb-3" />
)}
```

**Replace with:**
```typescript
{!isUser && message.thinking && (
  <EnhancedThinkingBlock 
    rawContent={message.thinking}
    isStreaming={false}
    tokenBudget={512}
    className="mb-3"
  />
)}
```

---

### Task 10.3: Add CSS Animations

**File:** `app/globals.css`

**Action:** Add to the end of the file (after existing styles)

```css
/* Enhanced Thinking Block Animations */
@keyframes fade-in {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.animate-fade-in {
  animation: fade-in 0.3s ease-out forwards;
}

/* Thinking pulse effect */
@keyframes thinking-pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

.animate-thinking-pulse {
  animation: thinking-pulse 2s ease-in-out infinite;
}

/* Smooth height transitions */
.transition-height {
  transition: max-height 0.3s ease-in-out;
}
```

---

## ✅ PHASE 11: SOVEREIGN WEB SEARCH

### Task 11.1: Create Search API Route

**File:** `app/api/search/route.ts` (NEW FILE)

**Action:** Create this file:

```typescript
import { NextRequest, NextResponse } from 'next/server';

const SEARXNG_URL = process.env.SEARXNG_URL || 'http://localhost:8888';

interface SearchResult {
  position: number;
  title: string;
  url: string;
  snippet: string;
  engine: string;
}

export async function POST(req: NextRequest) {
  try {
    const { query, num_results = 5 } = await req.json();

    if (!query || typeof query !== 'string') {
      return NextResponse.json(
        { error: 'Query is required and must be a string' },
        { status: 400 }
      );
    }

    // Validate num_results
    const resultCount = Math.min(Math.max(parseInt(num_results), 1), 10);

    // Build SearXNG URL
    const searchUrl = new URL('/search', SEARXNG_URL);
    searchUrl.searchParams.set('q', query);
    searchUrl.searchParams.set('format', 'json');
    searchUrl.searchParams.set('language', 'en');
    searchUrl.searchParams.set('safesearch', '1');
    searchUrl.searchParams.set('categories', 'general');

    // Call SearXNG with timeout
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 10000);

    const response = await fetch(searchUrl.toString(), {
      headers: {
        'Accept': 'application/json',
        'User-Agent': 'AetherAI/1.0',
      },
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      throw new Error(`SearXNG returned status ${response.status}`);
    }

    const data = await response.json();

    // Format results
    const results: SearchResult[] = (data.results || [])
      .slice(0, resultCount)
      .map((result: any, index: number) => ({
        position: index + 1,
        title: result.title || 'No title',
        url: result.url || '',
        snippet: result.content || result.description || '',
        engine: result.engine || 'unknown',
      }))
      .filter((r: SearchResult) => r.url); // Filter out results without URLs

    return NextResponse.json({
      success: true,
      query,
      results,
      total_results: results.length,
      search_metadata: {
        timestamp: new Date().toISOString(),
        engines_used: [...new Set(results.map(r => r.engine))],
        searxng_url: SEARXNG_URL,
      },
    });

  } catch (error) {
    console.error('Search API error:', error);
    
    const errorMessage = error instanceof Error ? error.message : 'Search failed';
    const isTimeout = errorMessage.includes('aborted');

    return NextResponse.json(
      { 
        success: false,
        error: isTimeout ? 'Search request timed out' : errorMessage,
        query: null,
      },
      { status: isTimeout ? 504 : 500 }
    );
  }
}
```

---

### Task 11.2: Create Tool Use Indicator Component

**File:** `components/chat/ToolUseIndicator.tsx` (NEW FILE)

**Action:** Create this file:

```typescript
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
```

---

### Task 11.3: Add Tool Definitions to Chat API

**File:** `app/api/chat/completions/route.ts`

**Action:** Add tool definitions after the SYSTEM_PROMPT constant

**Add after the SYSTEM_PROMPT (around line 35):**

```typescript
// Tool definitions for Apriel
const TOOLS = [
  {
    type: 'function',
    function: {
      name: 'web_search',
      description: 'Search the web for current information, recent news, or facts not in training data. Use when the user asks about current events, recent developments, or specific information you don\'t have.',
      parameters: {
        type: 'object',
        properties: {
          query: {
            type: 'string',
            description: 'The search query. Be specific and concise. Example: "latest AI infrastructure trends 2025"',
          },
          num_results: {
            type: 'integer',
            description: 'Number of results to return (1-10). Default is 5.',
            default: 5,
            minimum: 1,
            maximum: 10,
          },
        },
        required: ['query'],
      },
    },
  },
];
```

---

### Task 11.4: Implement Tool Call Handling

**File:** `app/api/chat/completions/route.ts`

**Action:** Update the fetch body to include tools (already done in Task 9.2, verify it's there)

**Then add tool call detection in the stream processing loop:**

**Find the stream processing section (inside `async start(controller)`):**

```typescript
for (const line of lines) {
  if (line.startsWith('data: ') && line !== 'data: [DONE]') {
    try {
      const json = JSON.parse(line.slice(6));
      const content = json.choices[0]?.delta?.content || '';
```

**Add BEFORE the existing `if (content.includes('<think>'))` check:**

```typescript
      // Handle tool calls
      if (json.choices[0]?.delta?.tool_calls) {
        const toolCall = json.choices[0].delta.tool_calls[0];
        
        if (toolCall?.function?.name === 'web_search') {
          try {
            // Parse tool arguments
            const args = JSON.parse(toolCall.function.arguments || '{}');
            
            // Emit tool use start event
            const toolStartPayload = JSON.stringify({
              type: 'tool_use',
              tool: 'web_search',
              query: args.query,
              status: 'searching',
            });
            controller.enqueue(encoder.encode(`data: ${toolStartPayload}\n\n`));
            
            // Call our search API
            const searchResponse = await fetch('http://localhost:3000/api/search', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                query: args.query,
                num_results: args.num_results || 5,
              }),
            });
            
            if (searchResponse.ok) {
              const searchData = await searchResponse.json();
              
              // Emit search results
              const toolResultPayload = JSON.stringify({
                type: 'tool_result',
                tool: 'web_search',
                query: args.query,
                results: searchData.results || [],
                status: 'complete',
              });
              controller.enqueue(encoder.encode(`data: ${toolResultPayload}\n\n`));
            } else {
              // Emit error
              const toolErrorPayload = JSON.stringify({
                type: 'tool_error',
                tool: 'web_search',
                error: 'Search failed',
              });
              controller.enqueue(encoder.encode(`data: ${toolErrorPayload}\n\n`));
            }
          } catch (e) {
            console.error('Tool call error:', e);
          }
        }
        continue;
      }
```

---

### Task 11.5: Update ChatInterface to Handle Tool Events

**File:** `components/chat/ChatInterface.tsx`

**Action:** Add tool event handling in the streaming callbacks

**Find the `streamChat` call (around line 50-80):**

**Add a new state variable at the top:**
```typescript
const [currentToolUse, setCurrentToolUse] = useState<{
  tool: string;
  query: string;
  results?: any[];
  isSearching: boolean;
} | null>(null);
```

**Add new callbacks to the streamChat call:**

```typescript
await streamChat(
  {
    messages: [
      ...messages,
      { role: 'user', content: content.trim() }
    ],
    model: currentModel === 'auto' ? 'apriel-1.5-15b-thinker' : currentModel,
    temperature: 0.7,
  },
  {
    onThinking: (chunk: string) => {
      thinkingContent += chunk;
      updateLastMessage({
        thinking: thinkingContent,
      });
    },

    onContent: (chunk: string) => {
      responseContent += chunk;
      updateLastMessage({
        content: responseContent,
      });
    },

    // NEW: Add these tool callbacks
    onToolUse: (data: any) => {
      if (data.tool === 'web_search') {
        setCurrentToolUse({
          tool: data.tool,
          query: data.query,
          results: data.results,
          isSearching: data.status === 'searching',
        });
      }
    },

    onToolResult: (data: any) => {
      if (data.tool === 'web_search') {
        setCurrentToolUse({
          tool: data.tool,
          query: data.query,
          results: data.results,
          isSearching: false,
        });
      }
    },

    onDone: () => {
      setIsStreaming(false);
      setCurrentToolUse(null); // Clear tool use on completion
    },

    onError: (error: string) => {
      console.error('Stream error:', error);
      updateLastMessage({
        content: responseContent || `Error: ${error}`,
      });
      setIsStreaming(false);
      setCurrentToolUse(null);
    },
  }
);
```

---

### Task 11.6: Display Tool Use in MessageList

**File:** `components/chat/MessageList.tsx`

**Action:** Import and add ToolUseIndicator

**Add import at top:**
```typescript
import { ToolUseIndicator } from './ToolUseIndicator';
```

**Find the streaming indicator section (around line 70-80):**

**Add BEFORE the streaming indicator:**

```typescript
{/* Tool use indicator - only during streaming */}
{isStreaming && currentToolUse && (
  <ToolUseIndicator
    tool={currentToolUse.tool}
    query={currentToolUse.query}
    results={currentToolUse.results}
    isSearching={currentToolUse.isSearching}
  />
)}

{/* Existing streaming indicator */}
{isStreaming && !currentToolUse && (
  <div className="flex items-center gap-2 text-aether-purple-light mb-4">
    {/* ... existing code ... */}
  </div>
)}
```

**Note:** You'll need to pass `currentToolUse` as a prop to MessageList from ChatInterface

**Update MessageList props:**
```typescript
interface MessageListProps {
  messages: MessageType[];
  isStreaming?: boolean;
  currentToolUse?: { tool: string; query: string; results?: any[]; isSearching: boolean } | null;
  className?: string;
}
```

---

### Task 11.7: Update streaming.ts Type Definitions

**File:** `lib/streaming.ts`

**Action:** Add tool callback types

**Find the StreamCallbacks interface:**

```typescript
export interface StreamCallbacks {
  onThinking?: (thinking: string) => void;
  onContent?: (chunk: string) => void;
  onModel?: (model: string, tokensUsed?: number) => void;
  onError?: (error: string) => void;
  onDone?: () => void;
}
```

**Replace with:**

```typescript
export interface StreamCallbacks {
  onThinking?: (thinking: string) => void;
  onContent?: (chunk: string) => void;
  onModel?: (model: string, tokensUsed?: number) => void;
  onToolUse?: (data: { tool: string; query: string; status: string; results?: any[] }) => void;
  onToolResult?: (data: { tool: string; query: string; results: any[]; status: string }) => void;
  onError?: (error: string) => void;
  onDone?: () => void;
}
```

**Update the parsing logic to handle new event types:**

**Find the switch statement (around line 85):**

```typescript
switch (parsed.type) {
  case 'thinking':
    callbacks.onThinking?.(parsed.content);
    break;

  case 'content':
    callbacks.onContent?.(parsed.content);
    break;

  case 'model':
    callbacks.onModel?.(parsed.model, parsed.tokens_used);
    break;

  case 'error':
    callbacks.onError?.(parsed.error);
    return;
}
```

**Add these cases:**

```typescript
switch (parsed.type) {
  case 'thinking':
    callbacks.onThinking?.(parsed.content);
    break;

  case 'content':
    callbacks.onContent?.(parsed.content);
    break;

  case 'model':
    callbacks.onModel?.(parsed.model, parsed.tokens_used);
    break;

  case 'tool_use':
    callbacks.onToolUse?.({
      tool: parsed.tool,
      query: parsed.query,
      status: parsed.status,
      results: parsed.results,
    });
    break;

  case 'tool_result':
    callbacks.onToolResult?.({
      tool: parsed.tool,
      query: parsed.query,
      results: parsed.results,
      status: parsed.status,
    });
    break;

  case 'error':
    callbacks.onError?.(parsed.error);
    return;
}
```

---

## ✅ PHASE 6: BRANDING & ASSETS

### Task 6.3: Update Tailwind Config

**File:** `tailwind.config.ts`

**Action:** Replace the entire colors section in `theme.extend`

**Find the existing colors config and replace with:**

```typescript
colors: {
  // Deep Space Purple Palette (AetherAI Brand)
  'aether-purple-darkest': '#0a0515',
  'aether-purple-dark': '#1a0b2e',
  'aether-purple-mid': '#2d1b4e',
  'aether-purple-light': '#4a2c6d',
  'aether-purple-accent': '#6b4a8e',
  
  // High Voltage Orange (Brand Accent)
  'aether-orange': '#ff6b35',
  'aether-orange-glow': '#ff8555',
  'aether-orange-dark': '#cc5529',
  
  // Industrial Neutrals
  'aether-steel': '#8892b0',
  'aether-graphite': '#1e1e2e',
  'aether-white': '#e6f1ff',
  'aether-text': '#e6f1ff',
  'aether-text-muted': '#a8b2d1',
  
  // Semantic Colors
  'aether-bg-dark': '#0a0515',
  'aether-bg-card': '#1a0b2e',
  'aether-bg-hover': '#2d1b4e',
  
  // Borders
  'aether-border': '#2d1b4e',
  'aether-border-light': '#4a2c6d',
  
  // Legacy alias (for compatibility)
  'aether-indigo-light': '#4a2c6d',
},
```

---

### Task 6.4: Copy Logo Assets

**Action:** Copy logo files from local system to public directory

**Run these commands:**

```bash
# From project root
cp ~/Pictures/AetherAI-Branding-\&-Logo/favicon/* ./public/

# Verify files copied
ls -la public/ | grep -E "(logo|favicon|apple|android)"
```

**Expected files in public/:**
- `logo.png` (1024x1024)
- `logo-256.png`
- `favicon.ico`
- `favicon-16x16.png`
- `favicon-32x32.png`
- `favicon-48x48.png`
- `apple-touch-icon.png`
- `android-chrome-192x192.png`

---

### Task 6.5: Update Layout Metadata

**File:** `app/layout.tsx`

**Action:** Update metadata export

**Find the metadata export (around line 10-15):**

**Replace with:**

```typescript
export const metadata = {
  title: 'AetherAI - Sovereign AI Platform',
  description: 'The American Standard for Sovereign AI. Powered by Apriel on US infrastructure.',
  icons: {
    icon: [
      { url: '/favicon-16x16.png', sizes: '16x16', type: 'image/png' },
      { url: '/favicon-32x32.png', sizes: '32x32', type: 'image/png' },
      { url: '/favicon-48x48.png', sizes: '48x48', type: 'image/png' },
    ],
    apple: '/apple-touch-icon.png',
    other: [
      { rel: 'icon', url: '/favicon.ico' },
    ],
  },
  manifest: '/site.webmanifest',
};
```

---

### Task 6.6: Create Web Manifest

**File:** `public/site.webmanifest` (NEW FILE)

**Action:** Create this file:

```json
{
  "name": "AetherAI",
  "short_name": "AetherAI",
  "description": "The American Standard for Sovereign AI",
  "icons": [
    {
      "src": "/android-chrome-192x192.png",
      "sizes": "192x192",
      "type": "image/png"
    },
    {
      "src": "/logo-256.png",
      "sizes": "256x256",
      "type": "image/png"
    }
  ],
  "theme_color": "#1a0b2e",
  "background_color": "#0a0515",
  "display": "standalone",
  "start_url": "/"
}
```

---

### Task 6.7: Update Logo Component

**File:** `components/shared/Logo.tsx`

**Action:** Update to use new logo assets

**Replace the entire file with:**

```typescript
'use client';

interface LogoProps {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
  showText?: boolean;
}

export function Logo({ size = 'md', className = '', showText = true }: LogoProps) {
  const sizeClasses = {
    sm: 'h-8',
    md: 'h-12',
    lg: 'h-16',
  };

  return (
    <div className={`flex items-center gap-3 ${className}`}>
      <img
        src="/logo.png"
        alt="AetherAI"
        className={`${sizeClasses[size]} w-auto`}
      />
      {showText && (
        <span className="text-xl font-bold bg-gradient-to-r from-aether-purple-light to-aether-orange bg-clip-text text-transparent">
          AetherAI
        </span>
      )}
    </div>
  );
}

export function LogoWithTagline({ className = '' }: { className?: string }) {
  return (
    <div className={`flex flex-col items-center ${className}`}>
      <img src="/logo.png" alt="AetherAI" className="h-24 w-auto mb-4" />
      <h1 className="text-3xl font-bold bg-gradient-to-r from-aether-purple-light to-aether-orange bg-clip-text text-transparent">
        AetherAI
      </h1>
      <p className="text-aether-text-muted text-sm mt-2">
        The American Standard for Sovereign AI
      </p>
    </div>
  );
}
```

---

## ✅ PHASE 12: ENVIRONMENT SETUP

### Task 12.1: Update Environment Variables

**File:** `.env.local`

**Action:** Add SearXNG configuration

**Add these lines:**

```bash
# SearXNG Configuration
SEARXNG_URL=http://localhost:8888

# Existing vars (verify they're present)
AETHER_UPSTREAM_URL=https://api.aetherpro.tech/v1/chat/completions
AETHER_API_KEY=sk-aether-sovereign-master-key-2026
NEXT_PUBLIC_MODEL_ID=apriel-1.5-15b-thinker
```

---

### Task 12.2: Verify SearXNG is Running

**Action:** Test SearXNG before deployment

**Run:**
```bash
curl "http://localhost:8888/search?q=test&format=json" | jq '.results[0]'
```

**Expected:** JSON response with search results

**If not running:**
```bash
cd ~/path/to/searxng-directory
docker-compose -f searxng-compose.yml up -d
```

---

## ✅ PHASE 13: TESTING & VALIDATION

### Task 13.1: Build & Type Check

**Action:** Verify no TypeScript errors

```bash
npm run build
```

**Expected:** Clean build with no errors

**If errors occur:**
- Review error messages
- Check imports and type definitions
- Verify all new files are created

---

### Task 13.2: Test Locally

**Action:** Run dev server and test features

```bash
npm run dev
```

**Test checklist:**
- [ ] Homepage loads
- [ ] Can send a message
- [ ] Thinking block appears and expands
- [ ] Timeline view shows steps
- [ ] Response is concise (<300 words)
- [ ] Logo displays correctly
- [ ] Colors match deep purple theme

**Test web search:**
- [ ] Send: "What are the latest AI infrastructure trends?"
- [ ] Tool use indicator appears
- [ ] Search completes with results
- [ ] Response cites sources

---

### Task 13.3: Test Thinking Display

**Action:** Send complex question to trigger thinking

**Test query:** "Explain how to scale vLLM inference across multiple GPUs with optimal memory usage"

**Verify:**
- [ ] Thinking block appears (collapsed)
- [ ] Click to expand shows timeline
- [ ] Steps are categorized (analysis, calculation, reasoning, conclusion)
- [ ] Token budget indicator shows progress
- [ ] "Full Detail" view shows raw thinking
- [ ] Final response is concise with key points

---

## ✅ PHASE 14: DEPLOYMENT

### Task 14.1: Commit Changes

```bash
git add .
git commit -m "feat: Enterprise thinking display + sovereign web search + response quality tuning

- Add EnhancedThinkingBlock with 3-tier display (collapsed/timeline/detailed)
- Integrate SearXNG for sovereign web search
- Reduce response verbosity with tuned parameters
- Update to deep purple brand colors
- Add Y-node logo and favicon package
- Implement tool calling with visual indicators
- Add CSS animations for smooth UX"
```

---

### Task 14.2: Push to Vercel

```bash
git push origin main
```

**Vercel will auto-deploy.**

---

### Task 14.3: Update Vercel Environment Variables

**Action:** In Vercel Dashboard

1. Go to Project Settings → Environment Variables
2. Add: `SEARXNG_URL` = `http://localhost:8888`
   - **Note:** This won't work in Vercel's serverless environment
   - You need to either:
     - Option A: Deploy SearXNG on a separate server with public URL
     - Option B: Use Vercel's deployment and access via internal network
     - Option C: For now, test locally only

**Recommended:** Deploy SearXNG on your L40S-90 with public access:

```bash
# On L40S-90, update docker-compose to use public URL
# Then expose via nginx:

# Add to your nginx config:
location /search {
    proxy_pass http://localhost:8888/search;
    proxy_set_header Host $host;
}

# Then set in Vercel:
SEARXNG_URL=https://api.aetherpro.tech
```

---

## 📊 SUCCESS CRITERIA

**After deployment, verify:**

1. **✅ Response Quality**
   - Responses are 150-300 words (down from 500-1000)
   - No repetitive "We can also mention" patterns
   - Clear, concise answers with 2-3 bullet points max

2. **✅ Thinking Display**
   - Thinking block shows in collapsed view by default
   - Timeline view displays steps with correct categorization
   - Token budget indicator works
   - Smooth animations between view modes

3. **✅ Web Search**
   - Search tool activates on current events queries
   - Tool use indicator displays during search
   - Results show with clickable links
   - Citations appear in final response

4. **✅ Brand**
   - Deep purple color scheme throughout
   - Y-node logo displays correctly
   - Favicon shows in browser tab
   - Professional, polished appearance

5. **✅ Performance**
   - Page loads in <2 seconds
   - Thinking display renders smoothly
   - Search completes in <3 seconds
   - No console errors

---

## 🐛 TROUBLESHOOTING

### Issue: SearXNG not responding

**Check:**
```bash
docker ps | grep searxng
curl http://localhost:8888/search?q=test&format=json
```

**Fix:**
```bash
docker-compose -f searxng-compose.yml restart
docker logs aether-search
```

---

### Issue: Tool calls not triggering

**Check:**
- vLLM supports tool calling for Apriel model
- TOOLS array is defined in route.ts
- Callbacks include onToolUse/onToolResult

**Test manually:**
```bash
curl -X POST https://api.aetherpro.tech/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-aether-sovereign-master-key-2026" \
  -d '{
    "model": "apriel-1.5-15b-thinker",
    "messages": [{"role": "user", "content": "What are the latest AI trends?"}],
    "tools": [{"type": "function", "function": {"name": "web_search"}}],
    "stream": false
  }'
```

---

### Issue: Thinking block not parsing steps

**Check:**
- Raw thinking content contains step patterns
- EnhancedThinkingBlock component imported correctly
- Regex patterns in detectStepType() match your model's output

**Debug:**
```typescript
// Add console.log in EnhancedThinkingBlock useEffect:
console.log('Raw thinking:', rawContent);
console.log('Parsed steps:', parsedSteps);
```

---

### Issue: Colors not updating

**Check:**
```bash
# Rebuild Tailwind classes
npm run build

# Check if tailwind.config.ts was updated
grep "aether-purple-darkest" tailwind.config.ts
```

---

## 📝 NOTES

- **SearXNG:** Currently configured for local development. For production on Vercel, deploy SearXNG on L40S-90 with public URL and update `SEARXNG_URL` env var.

- **Tool Calling:** Apriel model supports tool calling natively. vLLM handles the function call parsing. We just need to detect the tool_calls in the stream and execute them.

- **Response Length:** Max tokens set to 600 (~450 words). Adjust if needed, but this forces conciseness.

- **Thinking Budget:** Set to 512 tokens. This allows detailed reasoning without excessive verbosity.

- **Search Results:** Limited to 5 by default. Can be increased up to 10 if needed.

---

## 🎯 FINAL VALIDATION

**Send this test query after deployment:**

> "What are the latest developments in sovereign AI infrastructure, and how does it compare to traditional cloud AI deployment?"

**Expected behavior:**
1. Thinking block appears (collapsed)
2. Tool use indicator shows "Searching the web..."
3. Search completes with 3-5 results displayed
4. Thinking block updates with reasoning steps
5. Final response:
   - References search results with citations
   - 200-300 words
   - 2-3 bullet points
   - Clear, professional tone
   - Offers to elaborate

**If all criteria met: ✅ DEPLOYMENT SUCCESSFUL**

---

## 📧 SUPPORT

If issues arise during deployment:
1. Check console logs for errors
2. Review Network tab for failed requests
3. Test each component individually
4. Verify environment variables are set
5. Check SearXNG is accessible

---

**END OF SPECIFICATION**

*Generated: 2025-11-23*
*Version: 1.0*
*Status: Ready for Claude Code execution*
</parameter>
