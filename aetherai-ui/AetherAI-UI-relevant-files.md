ChatInterface.tsx:

'use client';

import { useState } from 'react';
import { useChatStore } from '@/lib/stores/chatStore';
import { MessageList } from './MessageList';
import { InputBar } from './InputBar';
import { Sidebar } from './Sidebar';
import { streamChat } from '@/lib/streaming';

export default function ChatInterface() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [currentToolUse, setCurrentToolUse] = useState<{
    tool: string;
    query: string;
    results?: any[];
    isSearching: boolean;
  } | null>(null);

  const {
    messages,
    isStreaming,
    currentModel,
    addMessage,
    updateLastMessage,
    setIsStreaming,
  } = useChatStore();

  const handleSendMessage = async (content: string) => {
    if (!content.trim() || isStreaming) return;

    // Add user message
    addMessage({
      role: 'user',
      content: content.trim(),
    });

    // Prepare for assistant response
    setIsStreaming(true);

    // Create empty assistant message that we'll update
    addMessage({
      role: 'assistant',
      content: '',
      thinking: '',
    });

    // Track response content as it streams
    let thinkingContent = '';
    let responseContent = '';

    try {
      const contextMessages = useChatStore.getState().getContext();
      await streamChat(
        {
          messages: contextMessages,
          model: currentModel === 'auto' ? 'apriel-1.5-15b-thinker' : currentModel,
          temperature: 0.7,
          enable_tools: true,
        },
        {
          // === Thinking Callbacks ===
          onThinkingStart: () => {
            // Optional: Show thinking indicator
          },

          onThinking: (chunk: string) => {
            thinkingContent += chunk;
            updateLastMessage({
              thinking: thinkingContent,
            });
          },

          onThinkingEnd: (fullThinking: string) => {
            // Use the complete thinking if provided
            if (fullThinking) {
              thinkingContent = fullThinking;
              updateLastMessage({
                thinking: thinkingContent,
              });
            }
          },

          // === Content Callbacks ===
          onContent: (chunk: string) => {
            responseContent += chunk;
            updateLastMessage({
              content: responseContent,
            });
          },

          onFinalStart: () => {
            // Optional: Indicate final response starting
          },

          onFinalResponse: (response: string) => {
            // Use the complete final response if provided
            if (response) {
              responseContent = response;
              updateLastMessage({
                content: responseContent,
              });
            }
          },

          // === Tool Callbacks ===
          onToolUse: (data) => {
            setCurrentToolUse({
              tool: data.tool,
              query: data.query,
              results: data.results,
              isSearching: data.status === 'searching',
            });
          },

          onToolCallsDetected: (calls) => {
            // Multiple tools detected - show first one
            if (calls.length > 0) {
              const firstCall = calls[0];
              setCurrentToolUse({
                tool: firstCall.name,
                query: firstCall.arguments?.query || '',
                isSearching: true,
              });
            }
          },

          onToolExecuting: (tool, args) => {
            setCurrentToolUse({
              tool,
              query: args.query || '',
              isSearching: true,
            });
          },

          onToolResult: (data) => {
            setCurrentToolUse({
              tool: data.tool,
              query: data.query,
              results: data.results,
              isSearching: false,
            });

            // Auto-clear tool display after a delay
            setTimeout(() => {
              setCurrentToolUse(null);
            }, 2000);
          },

          onToolError: (tool, error) => {
            console.error(`Tool ${tool} error:`, error);
            setCurrentToolUse(null);
          },

          // === Completion Callbacks ===
          onDone: (finalResponse?: string) => {
            // If final response provided, use it
            if (finalResponse && !responseContent) {
              updateLastMessage({
                content: finalResponse,
              });
            }
            setIsStreaming(false);
            setCurrentToolUse(null);
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
    } catch (error) {
      console.error('Chat error:', error);
      setIsStreaming(false);
      setCurrentToolUse(null);
    }
  };

  return (
    <div className="flex h-screen bg-aether-bg-dark text-aether-text">
      {/* Sidebar - Desktop always visible, Mobile toggleable */}
      <div
        className={`
          fixed md:relative z-50 md:z-auto
          w-80 h-full
          transform transition-transform duration-300 ease-in-out
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}
        `}
      >
        <Sidebar onClose={() => setSidebarOpen(false)} />
      </div>

      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Main chat area */}
      <div className="flex-1 flex flex-col">
        {/* Header with mobile menu toggle */}
        <header className="h-16 border-b border-aether-indigo-light flex items-center px-4 md:px-6 bg-aether-bg-card">
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="md:hidden mr-4 text-aether-text hover:text-aether-purple-light transition-colors"
          >
            <svg
              width="24"
              height="24"
              viewBox="0 0 24 24"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                d="M3 12H21M3 6H21M3 18H21"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </button>

          <div className="flex-1">
            <h1 className="text-lg font-semibold bg-gradient-to-r from-aether-purple-light to-aether-indigo-light bg-clip-text text-transparent">
              AetherAI
            </h1>
            <p className="text-xs text-aether-text-muted">
              Powered by Apriel • Sovereign US Infrastructure
            </p>
          </div>

          {/* Model badge */}
          <div className="hidden md:flex items-center gap-2 px-3 py-1.5 bg-aether-bg-dark rounded-full border border-aether-indigo-light">
            <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
            <span className="text-xs font-medium">
              {currentModel === 'auto' ? 'Apriel (Auto)' : currentModel.toUpperCase()}
            </span>
          </div>
        </header>

        {/* Messages */}
        <MessageList 
          messages={messages} 
          isStreaming={isStreaming} 
          currentToolUse={currentToolUse} 
        />

        {/* Input */}
        <InputBar onSend={handleSendMessage} disabled={isStreaming} />
      </div>
    </div>
  );
}

route.ts:

import { NextRequest, NextResponse } from 'next/server';

// --- SYSTEM PROMPT (keeps Apriel behavior, works for 1.5 & 1.6) ---
const SYSTEM_PROMPT = `You are Apriel, Sovereign AI of AetherPro Technologies.

ROLE & PERSONA:
- You are a Senior Technical Advisor and AI Architect for sovereign infrastructure.
- Tone: Professional, direct, high-signal. No fluff.
- Voice: Modern American Engineering (e.g., "Let's deploy this," not "We shall henceforth").

CRITICAL OUTPUT RULES (DO NOT VIOLATE):
1. START with your reasoning process enclosed in <think>...</think> tags.
2. AFTER reasoning, output the marker "[BEGIN FINAL RESPONSE]".
3. PROVIDE your actual response to the user AFTER that marker.

STRUCTURE:
- Direct Answer: 1-2 sentences immediately after the final response marker.
- Details: Use bullet points for clarity.
- Tool Usage: If you need to search, output the tool call clearly.

YOUR GOAL:
Solve the user's problem with sovereign, self-hosted solutions. Privacy is the product.`;

const TOOLS = [
  {
    type: 'function',
    function: {
      name: 'web_search',
      description:
        'Search the web for current information, recent news, or facts not in training data.',
      parameters: {
        type: 'object',
        properties: {
          query: {
            type: 'string',
            description: 'The search query. Be specific and concise.'
          },
          num_results: {
            type: 'integer',
            description: 'Number of results to return (1-10). Default is 5.',
            default: 5
          }
        },
        required: ['query']
      }
    }
  }
];

// Markers we strip out before sending to the frontend
const ARTIFACT_PATTERNS = [
  /\[BEGIN FINAL RESPONSE\]/gi,
  /\[END FINAL RESPONSE\]/gi,     // 1.5-style
  /<\|end\|>/gi,                  // 1.6-style
  /<\|endoftext\|>/gi
];

function cleanArtifacts(content: string): string {
  let cleaned = content;
  for (const pattern of ARTIFACT_PATTERNS) {
    cleaned = cleaned.replace(pattern, '');
  }
  return cleaned;
}

/**
 * VERY SIMPLE stream parser:
 * - Splits <think>...</think> blocks into "thinking" events
 * - Everything else is "content"
 * - No buffering games, so we NEVER swallow tokens.
 * Works for both 1.5 and 1.6; frontend just gets chunks.
 */
class StreamParser {
  private pendingToolCall: { name?: string; arguments: string } | null = null;

  parse(
    chunk: string
  ): Array<{ type: 'thinking' | 'content'; content: string }> {
    const results: Array<{ type: 'thinking' | 'content'; content: string }> =
      [];

    let remaining = chunk;

    while (true) {
      const start = remaining.indexOf('<think>');
      const end = remaining.indexOf('</think>');

      if (start !== -1 && end !== -1 && end > start) {
        // Text before <think> is normal content
        const before = remaining.slice(0, start);
        if (before.trim()) {
          results.push({
            type: 'content',
            content: cleanArtifacts(before)
          });
        }

        // Actual thinking block
        const thought = remaining.slice(start + 7, end);
        if (thought.trim()) {
          results.push({
            type: 'thinking',
            content: thought
          });
        }

        // Continue parsing after </think>
        remaining = remaining.slice(end + 8);
        continue;
      }

      // No complete <think> block left, treat the rest as content
      if (remaining.trim()) {
        results.push({
          type: 'content',
          content: cleanArtifacts(remaining)
        });
      }
      break;
    }

    return results;
  }

  // Tool call accumulator stays the same
  accumulateToolCall(delta: any): {
    complete: boolean;
    toolCall?: { name: string; arguments: any };
  } {
    if (!this.pendingToolCall) this.pendingToolCall = { arguments: '' };
    if (delta.function?.name) this.pendingToolCall.name = delta.function.name;
    if (delta.function?.arguments)
      this.pendingToolCall.arguments += delta.function.arguments;

    if (this.pendingToolCall.name && this.pendingToolCall.arguments) {
      try {
        const args = JSON.parse(this.pendingToolCall.arguments);
        const result = {
          name: this.pendingToolCall.name,
          arguments: args
        };
        this.pendingToolCall = null;
        return { complete: true, toolCall: result };
      } catch {
        return { complete: false };
      }
    }
    return { complete: false };
  }

  // Nothing buffered long-term, so flush is a no-op
  flush(): Array<{ type: 'thinking' | 'content'; content: string }> {
    return [];
  }
}

export async function POST(req: NextRequest) {
  try {
    const { messages, model } = await req.json();

    // Inject system prompt in front of user messages
    const fullMessages = [
      { role: 'system', content: SYSTEM_PROMPT },
      ...messages
    ];

    // IMPORTANT: keep model name as "apriel" (LiteLLM mapping)
    const upstreamUrl =
      process.env.AETHER_UPSTREAM_URL ||
      'http://localhost:8001/v1/chat/completions';

    const upstreamResponse = await fetch(upstreamUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${
          process.env.AETHER_API_KEY ||
          'sk-aether-sovereign-master-key-2026'
        }`
      },
      body: JSON.stringify({
        model: model || 'apriel',
        messages: fullMessages,
        temperature: 0.6,
        repetition_penalty: 1.0,
        max_tokens: 8192,
        top_p: 0.95,
        stream: true,
        tools: TOOLS,
        tool_choice: 'auto'
      }),
      signal: AbortSignal.timeout(600000)
    });

    if (!upstreamResponse.ok) {
      const errText = await upstreamResponse.text();
      console.error('Upstream Error:', errText);
      throw new Error(
        `Upstream Error: ${upstreamResponse.status} - ${errText}`
      );
    }

    const encoder = new TextEncoder();
    const decoder = new TextDecoder();
    const parser = new StreamParser();

    const stream = new ReadableStream({
      async start(controller) {
        const emit = (payload: object) => {
          controller.enqueue(
            encoder.encode(`data: ${JSON.stringify(payload)}\n\n`)
          );
        };

        try {
          const reader = upstreamResponse.body?.getReader();
          if (!reader) {
            controller.close();
            return;
          }

          while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value, { stream: true });
            const lines = chunk.split('\n');

            for (const line of lines) {
              if (!line.startsWith('data: ')) continue;
              if (line === 'data: [DONE]') continue;

              try {
                const json = JSON.parse(line.slice(6));
                const delta = json.choices?.[0]?.delta;

                if (delta) {
                  // --- Tool calls ---
                  if (delta.tool_calls) {
                    const toolDelta = delta.tool_calls[0];
                    const { complete, toolCall } =
                      parser.accumulateToolCall(toolDelta);

                    if (complete && toolCall) {
                      emit({
                        type: 'tool_use',
                        tool: toolCall.name,
                        query: toolCall.arguments.query,
                        status: 'searching'
                      });

                      if (toolCall.name === 'web_search') {
                        try {
                          const searchResponse = await fetch(
                            process.env.SEARCH_API_URL ||
                              'http://localhost:3000/api/search',
                            {
                              method: 'POST',
                              headers: { 'Content-Type': 'application/json' },
                              body: JSON.stringify({
                                query: toolCall.arguments.query,
                                num_results: 5
                              })
                            }
                          );

                          if (searchResponse.ok) {
                            const data = await searchResponse.json();
                            emit({
                              type: 'tool_result',
                              tool: 'web_search',
                              query: toolCall.arguments.query,
                              results: data.results || [],
                              status: 'complete'
                            });
                          } else {
                            emit({
                              type: 'tool_error',
                              tool: 'web_search',
                              error: 'Search failed'
                            });
                          }
                        } catch (e) {
                          emit({
                            type: 'tool_error',
                            tool: 'web_search',
                            error: String(e)
                          });
                        }
                      }
                    }

                    continue;
                  }

                  // --- Normal text content (thinking + final) ---
                  const content = delta.content;
                  if (content) {
                    const segments = parser.parse(content);
                    for (const seg of segments) {
                      if (seg.content?.trim() || seg.type === 'thinking') {
                        emit({ type: seg.type, content: seg.content });
                      }
                    }
                  }
                } else {
                  // pass through any non-delta events (e.g. metadata)
                  emit(json);
                }
              } catch {
                // ignore malformed JSON lines
              }
            }
          }

          const remaining = parser.flush();
          for (const seg of remaining) {
            if (seg.content?.trim()) {
              emit({ type: seg.type, content: seg.content });
            }
          }

          controller.enqueue(encoder.encode('data: [DONE]\n\n'));
          controller.close();
        } catch (error) {
          console.error('Stream error:', error);
          controller.close();
        }
      }
    });

    return new NextResponse(stream, {
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        Connection: 'keep-alive'
      }
    });
  } catch (error: any) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}


streaming.ts:

import { NextRequest, NextResponse } from 'next/server';

// --- SYSTEM PROMPT (keeps Apriel behavior, works for 1.5 & 1.6) ---
const SYSTEM_PROMPT = `You are Apriel, Sovereign AI of AetherPro Technologies.

ROLE & PERSONA:
- You are a Senior Technical Advisor and AI Architect for sovereign infrastructure.
- Tone: Professional, direct, high-signal. No fluff.
- Voice: Modern American Engineering (e.g., "Let's deploy this," not "We shall henceforth").

CRITICAL OUTPUT RULES (DO NOT VIOLATE):
1. START with your reasoning process enclosed in <think>...</think> tags.
2. AFTER reasoning, output the marker "[BEGIN FINAL RESPONSE]".
3. PROVIDE your actual response to the user AFTER that marker.

STRUCTURE:
- Direct Answer: 1-2 sentences immediately after the final response marker.
- Details: Use bullet points for clarity.
- Tool Usage: If you need to search, output the tool call clearly.

YOUR GOAL:
Solve the user's problem with sovereign, self-hosted solutions. Privacy is the product.`;

const TOOLS = [
  {
    type: 'function',
    function: {
      name: 'web_search',
      description:
        'Search the web for current information, recent news, or facts not in training data.',
      parameters: {
        type: 'object',
        properties: {
          query: {
            type: 'string',
            description: 'The search query. Be specific and concise.'
          },
          num_results: {
            type: 'integer',
            description: 'Number of results to return (1-10). Default is 5.',
            default: 5
          }
        },
        required: ['query']
      }
    }
  }
];

// Markers we strip out before sending to the frontend
const ARTIFACT_PATTERNS = [
  /\[BEGIN FINAL RESPONSE\]/gi,
  /\[END FINAL RESPONSE\]/gi,     // 1.5-style
  /<\|end\|>/gi,                  // 1.6-style
  /<\|endoftext\|>/gi
];

function cleanArtifacts(content: string): string {
  let cleaned = content;
  for (const pattern of ARTIFACT_PATTERNS) {
    cleaned = cleaned.replace(pattern, '');
  }
  return cleaned;
}

/**
 * VERY SIMPLE stream parser:
 * - Splits <think>...</think> blocks into "thinking" events
 * - Everything else is "content"
 * - No buffering games, so we NEVER swallow tokens.
 * Works for both 1.5 and 1.6; frontend just gets chunks.
 */
class StreamParser {
  private pendingToolCall: { name?: string; arguments: string } | null = null;

  parse(
    chunk: string
  ): Array<{ type: 'thinking' | 'content'; content: string }> {
    const results: Array<{ type: 'thinking' | 'content'; content: string }> =
      [];

    let remaining = chunk;

    while (true) {
      const start = remaining.indexOf('<think>');
      const end = remaining.indexOf('</think>');

      if (start !== -1 && end !== -1 && end > start) {
        // Text before <think> is normal content
        const before = remaining.slice(0, start);
        if (before.trim()) {
          results.push({
            type: 'content',
            content: cleanArtifacts(before)
          });
        }

        // Actual thinking block
        const thought = remaining.slice(start + 7, end);
        if (thought.trim()) {
          results.push({
            type: 'thinking',
            content: thought
          });
        }

        // Continue parsing after </think>
        remaining = remaining.slice(end + 8);
        continue;
      }

      // No complete <think> block left, treat the rest as content
      if (remaining.trim()) {
        results.push({
          type: 'content',
          content: cleanArtifacts(remaining)
        });
      }
      break;
    }

    return results;
  }

  // Tool call accumulator stays the same
  accumulateToolCall(delta: any): {
    complete: boolean;
    toolCall?: { name: string; arguments: any };
  } {
    if (!this.pendingToolCall) this.pendingToolCall = { arguments: '' };
    if (delta.function?.name) this.pendingToolCall.name = delta.function.name;
    if (delta.function?.arguments)
      this.pendingToolCall.arguments += delta.function.arguments;

    if (this.pendingToolCall.name && this.pendingToolCall.arguments) {
      try {
        const args = JSON.parse(this.pendingToolCall.arguments);
        const result = {
          name: this.pendingToolCall.name,
          arguments: args
        };
        this.pendingToolCall = null;
        return { complete: true, toolCall: result };
      } catch {
        return { complete: false };
      }
    }
    return { complete: false };
  }

  // Nothing buffered long-term, so flush is a no-op
  flush(): Array<{ type: 'thinking' | 'content'; content: string }> {
    return [];
  }
}

export async function POST(req: NextRequest) {
  try {
    const { messages, model } = await req.json();

    // Inject system prompt in front of user messages
    const fullMessages = [
      { role: 'system', content: SYSTEM_PROMPT },
      ...messages
    ];

    // IMPORTANT: keep model name as "apriel" (LiteLLM mapping)
    const upstreamUrl =
      process.env.AETHER_UPSTREAM_URL ||
      'http://localhost:8001/v1/chat/completions';

    const upstreamResponse = await fetch(upstreamUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${
          process.env.AETHER_API_KEY ||
          'sk-aether-sovereign-master-key-2026'
        }`
      },
      body: JSON.stringify({
        model: model || 'apriel',
        messages: fullMessages,
        temperature: 0.6,
        repetition_penalty: 1.0,
        max_tokens: 8192,
        top_p: 0.95,
        stream: true,
        tools: TOOLS,
        tool_choice: 'auto'
      }),
      signal: AbortSignal.timeout(600000)
    });

    if (!upstreamResponse.ok) {
      const errText = await upstreamResponse.text();
      console.error('Upstream Error:', errText);
      throw new Error(
        `Upstream Error: ${upstreamResponse.status} - ${errText}`
      );
    }

    const encoder = new TextEncoder();
    const decoder = new TextDecoder();
    const parser = new StreamParser();

    const stream = new ReadableStream({
      async start(controller) {
        const emit = (payload: object) => {
          controller.enqueue(
            encoder.encode(`data: ${JSON.stringify(payload)}\n\n`)
          );
        };

        try {
          const reader = upstreamResponse.body?.getReader();
          if (!reader) {
            controller.close();
            return;
          }

          while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value, { stream: true });
            const lines = chunk.split('\n');

            for (const line of lines) {
              if (!line.startsWith('data: ')) continue;
              if (line === 'data: [DONE]') continue;

              try {
                const json = JSON.parse(line.slice(6));
                const delta = json.choices?.[0]?.delta;

                if (delta) {
                  // --- Tool calls ---
                  if (delta.tool_calls) {
                    const toolDelta = delta.tool_calls[0];
                    const { complete, toolCall } =
                      parser.accumulateToolCall(toolDelta);

                    if (complete && toolCall) {
                      emit({
                        type: 'tool_use',
                        tool: toolCall.name,
                        query: toolCall.arguments.query,
                        status: 'searching'
                      });

                      if (toolCall.name === 'web_search') {
                        try {
                          const searchResponse = await fetch(
                            process.env.SEARCH_API_URL ||
                              'http://localhost:3000/api/search',
                            {
                              method: 'POST',
                              headers: { 'Content-Type': 'application/json' },
                              body: JSON.stringify({
                                query: toolCall.arguments.query,
                                num_results: 5
                              })
                            }
                          );

                          if (searchResponse.ok) {
                            const data = await searchResponse.json();
                            emit({
                              type: 'tool_result',
                              tool: 'web_search',
                              query: toolCall.arguments.query,
                              results: data.results || [],
                              status: 'complete'
                            });
                          } else {
                            emit({
                              type: 'tool_error',
                              tool: 'web_search',
                              error: 'Search failed'
                            });
                          }
                        } catch (e) {
                          emit({
                            type: 'tool_error',
                            tool: 'web_search',
                            error: String(e)
                          });
                        }
                      }
                    }

                    continue;
                  }

                  // --- Normal text content (thinking + final) ---
                  const content = delta.content;
                  if (content) {
                    const segments = parser.parse(content);
                    for (const seg of segments) {
                      if (seg.content?.trim() || seg.type === 'thinking') {
                        emit({ type: seg.type, content: seg.content });
                      }
                    }
                  }
                } else {
                  // pass through any non-delta events (e.g. metadata)
                  emit(json);
                }
              } catch {
                // ignore malformed JSON lines
              }
            }
          }

          const remaining = parser.flush();
          for (const seg of remaining) {
            if (seg.content?.trim()) {
              emit({ type: seg.type, content: seg.content });
            }
          }

          controller.enqueue(encoder.encode('data: [DONE]\n\n'));
          controller.close();
        } catch (error) {
          console.error('Stream error:', error);
          controller.close();
        }
      }
    });

    return new NextResponse(stream, {
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        Connection: 'keep-alive'
      }
    });
  } catch (error: any) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}

chatStore:

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  thinking?: string;
  model?: string;
  timestamp: Date;
}

export interface Conversation {
  id: string;
  title: string;
  messages: Message[];
  model: string;
  createdAt: Date;
  updatedAt: Date;
  contextStartIndex?: number;
}

interface ChatState {
  // Current conversation
  messages: Message[];
  currentConversationId: string | null;
  isStreaming: boolean;

  // Model selection
  currentModel: 'apriel' | 'auto';

  // Conversations list
  conversations: Conversation[];

  // Actions
  addMessage: (message: Omit<Message, 'id' | 'timestamp'>) => void;
  updateLastMessage: (updates: Partial<Message>) => void;
  clearMessages: () => void;
  setIsStreaming: (streaming: boolean) => void;
  setCurrentModel: (model: 'apriel' | 'auto') => void;
  loadConversation: (conversationId: string) => void;
  createNewConversation: () => void;
  deleteConversation: (conversationId: string) => void;
  getContext: () => Message[];
  resetContext: () => void;
  getContextTokens: () => number;
}

export const useChatStore = create<ChatState>()(
  persist(
    (set, get) => ({
      // Initial state
      messages: [],
      currentConversationId: null,
      isStreaming: false,
      currentModel: 'auto',
      conversations: [],

      // Actions
      addMessage: (message) => {
        const newMessage: Message = {
          ...message,
          id: crypto.randomUUID(),
          timestamp: new Date(),
        };
  
        set((state) => {
          const messages = [...state.messages, newMessage];
          const currentId = state.currentConversationId;
          if (currentId) {
            const convIndex = state.conversations.findIndex(c => c.id === currentId);
            if (convIndex !== -1) {
              const conv = state.conversations[convIndex];
              const updatedConv: Conversation = {
                ...conv,
                updatedAt: new Date(),
                messages,
              };
              // Auto-title if first assistant message
              if (conv.messages.length === 0 && message.role === 'assistant') {
                const firstUser = state.messages.find(m => m.role === 'user');
                if (firstUser) {
                  updatedConv.title = firstUser.content.slice(0, 50) + '...';
                }
              }
              const conversations = [...state.conversations];
              conversations[convIndex] = updatedConv;
              return {
                messages,
                conversations,
              };
            }
          }
          return { messages };
        });
      },

  updateLastMessage: (updates) => {
    set((state) => {
      const messages = [...state.messages];
      const lastIndex = messages.length - 1;

      if (lastIndex >= 0) {
        messages[lastIndex] = {
          ...messages[lastIndex],
          ...updates,
        };
      }

      const currentId = state.currentConversationId;
      if (currentId) {
        const convIndex = state.conversations.findIndex(c => c.id === currentId);
        if (convIndex !== -1) {
          const conversations = [...state.conversations];
          conversations[convIndex] = {
            ...conversations[convIndex],
            messages,
            updatedAt: new Date(),
          };
          return { messages, conversations };
        }
      }
      return { messages };
    });
  },

  clearMessages: () => {
    set({ messages: [], currentConversationId: null });
  },

  setIsStreaming: (streaming) => {
    set({ isStreaming: streaming });
  },

  setCurrentModel: (model) => {
    set({ currentModel: model });
  },

  loadConversation: (conversationId) => {
    const conversation = get().conversations.find(
      (c) => c.id === conversationId
    );

    if (conversation) {
      set({
        messages: conversation.messages,
        currentConversationId: conversationId,
        currentModel: conversation.model as any,
      });
    }
  },

  createNewConversation: () => {
    const id = crypto.randomUUID();
    const now = new Date();
    const conv: Conversation = {
      id,
      title: 'New Chat',
      messages: [],
      model: get().currentModel,
      createdAt: now,
      updatedAt: now,
    };
    set((state) => ({
      conversations: [conv, ...state.conversations],
      currentConversationId: id,
      messages: [],
    }));
  },

  deleteConversation: (conversationId) => {
    set((state) => ({
      conversations: state.conversations.filter(
        (c) => c.id !== conversationId
      ),
    }));

    // If deleting current conversation, clear messages
    if (get().currentConversationId === conversationId) {
      get().clearMessages();
    }
  },

  getContext: () => {
    const MAX_CONTEXT_TURNS = 6;
    const { messages, conversations, currentConversationId } = get();
    const conv = conversations.find(c => c.id === currentConversationId);
    const start = conv?.contextStartIndex ?? 0;
    const slice = messages.slice(start);
    const core = slice.filter(m => m.role === 'user' || m.role === 'assistant');
    const tail = core.slice(-MAX_CONTEXT_TURNS * 2);
    return tail;
  },

  resetContext: () => {
    const { currentConversationId, conversations, messages } = get();
    if (currentConversationId) {
      const convIndex = conversations.findIndex(c => c.id === currentConversationId);
      if (convIndex !== -1) {
        const convs = [...conversations];
        convs[convIndex] = {
          ...convs[convIndex],
          contextStartIndex: messages.length,
        };
        set({ conversations: convs });
      }
    }
  },

  getContextTokens: () => {
    const ctx = get().getContext();
    const estimateTokens = (text: string): number => {
      const words = text.match(/\S+/g)?.length || 0;
      return Math.ceil(words * 1.3);
    };
    return ctx.reduce((sum, m) => sum + estimateTokens(m.content), 0);
  },
    }),
    {
      name: 'aetherai-chat-session',
      // Store only messages and model for free tier session memory
      partialize: (state) => ({
        messages: state.messages,
        currentModel: state.currentModel,
        currentConversationId: state.currentConversationId,
        conversations: state.conversations
      })
    }
  )
);


