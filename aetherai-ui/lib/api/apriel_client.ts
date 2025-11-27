/**
 * AetherPro Apriel Client SDK
 * ===========================
 * TypeScript client for Apriel Router with WebSocket streaming support.
 * Drop-in replacement for your existing ChatInterface.tsx
 * 
 * Usage:
 *   const client = new AprielClient({ baseUrl: 'http://localhost:8001' });
 *   
 *   // HTTP Streaming
 *   await client.chat(messages, {
 *     onThinking: (content) => console.log('Thinking:', content),
 *     onContent: (content) => console.log('Content:', content),
 *     onToolUse: (tool, args) => console.log('Tool:', tool, args),
 *   });
 *   
 *   // WebSocket (real-time bidirectional)
 *   const ws = client.connectWebSocket({
 *     onEvent: (event) => handleEvent(event),
 *   });
 *   ws.send(messages);
 */

export interface Message {
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: string;
  thinking?: string;
  tool_calls?: ToolCall[];
}

export interface ToolCall {
  name: string;
  arguments: Record<string, any>;
}

export interface StreamEvent {
  type: 
    | 'thinking_start'
    | 'thinking'
    | 'thinking_end'
    | 'content'
    | 'final_start'
    | 'final_response'
    | 'tool_calls_start'
    | 'tool_calls_detected'
    | 'tool_executing'
    | 'tool_result'
    | 'done'
    | 'error';
  content?: string;
  calls?: ToolCall[];
  tool?: string;
  arguments?: Record<string, any>;
  result?: any;
  response?: string;
  message?: string;
}

export interface ChatCallbacks {
  onThinkingStart?: () => void;
  onThinking?: (content: string) => void;
  onThinkingEnd?: (fullThinking: string) => void;
  onContent?: (content: string) => void;
  onFinalResponse?: (response: string) => void;
  onToolCallsDetected?: (calls: ToolCall[]) => void;
  onToolExecuting?: (tool: string, args: Record<string, any>) => void;
  onToolResult?: (tool: string, result: any) => void;
  onDone?: (response: string) => void;
  onError?: (error: string) => void;
}

export interface AprielClientConfig {
  baseUrl: string;
  model?: string;
  enableTools?: boolean;
  timeout?: number;
}

export class AprielClient {
  private baseUrl: string;
  private model: string;
  private enableTools: boolean;
  private timeout: number;

  constructor(config: AprielClientConfig) {
    this.baseUrl = config.baseUrl.replace(/\/$/, '');
    this.model = config.model || 'apriel-1.5-15b-thinker';
    this.enableTools = config.enableTools ?? true;
    this.timeout = config.timeout || 120000;
  }

  /**
   * Stream chat completion via HTTP SSE
   */
  async chat(messages: Message[], callbacks: ChatCallbacks): Promise<void> {
    const response = await fetch(`${this.baseUrl}/v1/chat/completions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        messages,
        model: this.model,
        enable_tools: this.enableTools,
        stream: true,
      }),
    });

    if (!response.ok) {
      const error = await response.text();
      callbacks.onError?.(error);
      throw new Error(`Chat request failed: ${response.status}`);
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('No response body');
    }

    const decoder = new TextDecoder();
    let thinkingBuffer = '';
    let contentBuffer = '';

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (!line.startsWith('data: ') || line === 'data: [DONE]') continue;

          try {
            const event: StreamEvent = JSON.parse(line.slice(6));
            this.handleEvent(event, callbacks, { thinkingBuffer, contentBuffer });

            // Update buffers
            if (event.type === 'thinking' && event.content) {
              thinkingBuffer += event.content;
            }
            if (event.type === 'content' && event.content) {
              contentBuffer += event.content;
            }
          } catch {
            // Ignore malformed JSON
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  }

  /**
   * Non-streaming chat completion
   */
  async chatSync(messages: Message[]): Promise<{
    thinking?: string;
    content: string;
    tool_calls?: ToolCall[];
  }> {
    const response = await fetch(`${this.baseUrl}/v1/chat/completions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        messages,
        model: this.model,
        enable_tools: this.enableTools,
        stream: false,
      }),
    });

    if (!response.ok) {
      throw new Error(`Chat request failed: ${response.status}`);
    }

    return response.json();
  }

  /**
   * Connect WebSocket for real-time bidirectional chat
   */
  connectWebSocket(callbacks: {
    onEvent: (event: StreamEvent) => void;
    onOpen?: () => void;
    onClose?: () => void;
    onError?: (error: Event) => void;
  }): AprielWebSocket {
    const wsUrl = this.baseUrl.replace(/^http/, 'ws') + '/ws/chat';
    return new AprielWebSocket(wsUrl, callbacks);
  }

  /**
   * Health check
   */
  async health(): Promise<{ status: string; model: string; timestamp: string }> {
    const response = await fetch(`${this.baseUrl}/health`);
    return response.json();
  }

  /**
   * Handle individual stream event
   */
  private handleEvent(
    event: StreamEvent,
    callbacks: ChatCallbacks,
    buffers: { thinkingBuffer: string; contentBuffer: string }
  ): void {
    switch (event.type) {
      case 'thinking_start':
        callbacks.onThinkingStart?.();
        break;

      case 'thinking':
        if (event.content) {
          callbacks.onThinking?.(event.content);
        }
        break;

      case 'thinking_end':
        callbacks.onThinkingEnd?.(event.content || buffers.thinkingBuffer);
        break;

      case 'content':
        if (event.content) {
          callbacks.onContent?.(event.content);
        }
        break;

      case 'final_response':
        callbacks.onFinalResponse?.(event.content || '');
        break;

      case 'tool_calls_detected':
        if (event.calls) {
          callbacks.onToolCallsDetected?.(event.calls);
        }
        break;

      case 'tool_executing':
        if (event.tool && event.arguments) {
          callbacks.onToolExecuting?.(event.tool, event.arguments);
        }
        break;

      case 'tool_result':
        if (event.tool) {
          callbacks.onToolResult?.(event.tool, event.result);
        }
        break;

      case 'done':
        callbacks.onDone?.(event.response || buffers.contentBuffer);
        break;

      case 'error':
        callbacks.onError?.(event.message || 'Unknown error');
        break;
    }
  }
}

/**
 * WebSocket wrapper for real-time chat
 */
export class AprielWebSocket {
  private ws: WebSocket;
  private callbacks: {
    onEvent: (event: StreamEvent) => void;
    onOpen?: () => void;
    onClose?: () => void;
    onError?: (error: Event) => void;
  };

  constructor(
    url: string,
    callbacks: {
      onEvent: (event: StreamEvent) => void;
      onOpen?: () => void;
      onClose?: () => void;
      onError?: (error: Event) => void;
    }
  ) {
    this.callbacks = callbacks;
    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      callbacks.onOpen?.();
    };

    this.ws.onmessage = (event) => {
      try {
        const data: StreamEvent = JSON.parse(event.data);
        callbacks.onEvent(data);
      } catch {
        // Ignore malformed messages
      }
    };

    this.ws.onclose = () => {
      callbacks.onClose?.();
    };

    this.ws.onerror = (error) => {
      callbacks.onError?.(error);
    };
  }

  /**
   * Send messages to the WebSocket
   */
  send(messages: Message[], model?: string): void {
    this.ws.send(
      JSON.stringify({
        messages,
        model,
      })
    );
  }

  /**
   * Close the WebSocket connection
   */
  close(): void {
    this.ws.close();
  }

  /**
   * Check if WebSocket is connected
   */
  get isConnected(): boolean {
    return this.ws.readyState === WebSocket.OPEN;
  }
}

// ============================================================================
// React Hook (Optional - for easy integration)
// ============================================================================

import { useState, useCallback, useRef, useEffect } from 'react';

export interface UseAprielOptions {
  baseUrl: string;
  model?: string;
  enableTools?: boolean;
  useWebSocket?: boolean;
}

export interface UseAprielReturn {
  messages: Message[];
  isStreaming: boolean;
  thinking: string;
  currentToolUse: { tool: string; query: string; isSearching: boolean } | null;
  sendMessage: (content: string) => Promise<void>;
  clearMessages: () => void;
  error: string | null;
}

export function useApriel(options: UseAprielOptions): UseAprielReturn {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [thinking, setThinking] = useState('');
  const [currentToolUse, setCurrentToolUse] = useState<{
    tool: string;
    query: string;
    isSearching: boolean;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const clientRef = useRef<AprielClient | null>(null);

  // Initialize client
  useEffect(() => {
    clientRef.current = new AprielClient({
      baseUrl: options.baseUrl,
      model: options.model,
      enableTools: options.enableTools,
    });
  }, [options.baseUrl, options.model, options.enableTools]);

  const sendMessage = useCallback(
    async (content: string) => {
      if (!clientRef.current || isStreaming) return;

      const userMessage: Message = { role: 'user', content };
      setMessages((prev) => [...prev, userMessage]);
      setIsStreaming(true);
      setThinking('');
      setError(null);

      // Create placeholder for assistant response
      const assistantMessage: Message = { role: 'assistant', content: '', thinking: '' };
      setMessages((prev) => [...prev, assistantMessage]);

      let thinkingBuffer = '';
      let contentBuffer = '';

      try {
        await clientRef.current.chat([...messages, userMessage], {
          onThinking: (chunk) => {
            thinkingBuffer += chunk;
            setThinking(thinkingBuffer);
            setMessages((prev) => {
              const updated = [...prev];
              const last = updated[updated.length - 1];
              if (last.role === 'assistant') {
                last.thinking = thinkingBuffer;
              }
              return updated;
            });
          },

          onContent: (chunk) => {
            contentBuffer += chunk;
            setMessages((prev) => {
              const updated = [...prev];
              const last = updated[updated.length - 1];
              if (last.role === 'assistant') {
                last.content = contentBuffer;
              }
              return updated;
            });
          },

          onToolExecuting: (tool, args) => {
            setCurrentToolUse({
              tool,
              query: args.query || '',
              isSearching: true,
            });
          },

          onToolResult: (tool, result) => {
            setCurrentToolUse({
              tool,
              query: result?.query || '',
              isSearching: false,
            });
          },

          onDone: () => {
            setIsStreaming(false);
            setCurrentToolUse(null);
          },

          onError: (err) => {
            setError(err);
            setIsStreaming(false);
          },
        });
      } catch (e) {
        setError(String(e));
        setIsStreaming(false);
      }
    },
    [messages, isStreaming]
  );

  const clearMessages = useCallback(() => {
    setMessages([]);
    setThinking('');
    setError(null);
  }, []);

  return {
    messages,
    isStreaming,
    thinking,
    currentToolUse,
    sendMessage,
    clearMessages,
    error,
  };
}