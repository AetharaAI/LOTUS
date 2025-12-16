/**
 * SSE Streaming Client for Apriel Router
 * =======================================
 * Handles Server-Sent Events for real-time chat streaming.
 * Supports 3-pass routing: thinking → tool execution → final response
 */

const API_URL = '/api';

export interface StreamCallbacks {
  // Thinking events
  onThinkingStart?: () => void;
  onThinking?: (chunk: string) => void;
  onThinkingEnd?: (fullThinking: string) => void;

  // Content events
  onContent?: (chunk: string) => void;
  onFinalStart?: () => void;
  onFinalResponse?: (response: string) => void;

  // Tool events
  onToolUse?: (data: { tool: string; query: string; status: string; results?: any[] }) => void;
  onToolCallsDetected?: (calls: Array<{ name: string; arguments: any }>) => void;
  onToolExecuting?: (tool: string, args: Record<string, any>) => void;
  onToolResult?: (data: { tool: string; query: string; results: any[]; status: string }) => void;
  onToolError?: (tool: string, error: string) => void;

  // Meta events
  onModel?: (model: string, tokensUsed?: number) => void;
  onError?: (error: string) => void;
  onDone?: (response?: string) => void;
}

export interface ChatRequest {
  messages: Array<{ role: string; content: string; thinking?: string; tool_calls?: any[] }>;
  model?: string;
  temperature?: number;
  max_tokens?: number;
  enable_tools?: boolean;
}

export async function streamChat(
  request: ChatRequest,
  callbacks: StreamCallbacks
): Promise<void> {
  try {
    const response = await fetch(`${API_URL}/chat/completions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        ...request,
        stream: true,
        enable_tools: request.enable_tools ?? true,
      }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('No response body');
    }

    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();

      if (done) {
        callbacks.onDone?.();
        break;
      }

      buffer += decoder.decode(value, { stream: true });

      // Process complete events
      const events = buffer.split('\n\n');
      buffer = events.pop() || '';

      for (const event of events) {
        if (!event.trim()) continue;

        // Parse SSE event
        const lines = event.split('\n');
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.substring(6);

            if (data === '[DONE]') {
              callbacks.onDone?.();
              return;
            }

            try {
              const parsed = JSON.parse(data);
              handleStreamEvent(parsed, callbacks);
            } catch (e) {
              // Ignore malformed JSON chunks
              console.debug('Skipping malformed SSE chunk:', data.slice(0, 50));
            }
          }
        }
      }
    }
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';
    callbacks.onError?.(errorMessage);
  }
}

/**
 * Handle individual stream events from Apriel Router
 */
function handleStreamEvent(parsed: any, callbacks: StreamCallbacks): void {
  const eventType = parsed.type;

  switch (eventType) {
    // === Thinking Events ===
    case 'thinking_start':
      callbacks.onThinkingStart?.();
      break;

    case 'thinking':
      if (parsed.content) {
        callbacks.onThinking?.(parsed.content);
      }
      break;

    case 'thinking_end':
      callbacks.onThinkingEnd?.(parsed.content || '');
      break;

    // === Content Events ===
    case 'content':
      if (parsed.content) {
        callbacks.onContent?.(parsed.content);
      }
      break;

    case 'final_start':
      callbacks.onFinalStart?.();
      break;

    case 'final_response':
      callbacks.onFinalResponse?.(parsed.content || '');
      break;

    // === Tool Events ===
    case 'tool_use':
      callbacks.onToolUse?.({
        tool: parsed.tool,
        query: parsed.query,
        status: parsed.status || 'searching',
        results: parsed.results,
      });
      break;

    case 'tool_calls_detected':
      callbacks.onToolCallsDetected?.(parsed.calls || []);
      break;

    case 'tool_calls_start':
      // Tool calls starting to stream
      break;

    case 'tool_executing':
      callbacks.onToolExecuting?.(parsed.tool, parsed.arguments || {});
      break;

    case 'tool_result':
      callbacks.onToolResult?.({
        tool: parsed.tool,
        query: parsed.result?.query || parsed.query || '',
        results: parsed.result?.results || parsed.results || [],
        status: 'complete',
      });
      break;

    case 'tool_error':
      callbacks.onToolError?.(parsed.tool, parsed.error || 'Tool execution failed');
      break;

    // === Meta Events ===
    case 'model':
      callbacks.onModel?.(parsed.model, parsed.tokens_used);
      break;

    case 'error':
      callbacks.onError?.(parsed.error || parsed.message || 'Unknown error');
      break;

    case 'done':
      callbacks.onDone?.(parsed.response);
      break;

    default:
      // Unknown event type - log for debugging
      console.debug('Unknown stream event:', eventType, parsed);
  }
}

/**
 * Non-streaming chat completion (fallback)
 */
export async function chatCompletion(
  request: ChatRequest
): Promise<{ content: string; thinking?: string; model: string; tool_calls?: any[] }> {
  const response = await fetch(`${API_URL}/chat/completions`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      ...request,
      stream: false,
    }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
  }

  return response.json();
}

/**
 * WebSocket client for real-time bidirectional chat
 * Use this for lower latency in production
 */
export class AprielWebSocket {
  private ws: WebSocket | null = null;
  private callbacks: StreamCallbacks = {};
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;

  constructor(private baseUrl: string = '') {
    // Convert HTTP URL to WebSocket URL
    if (!baseUrl) {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      this.baseUrl = `${protocol}//${window.location.host}`;
    }
  }

  connect(callbacks: StreamCallbacks): Promise<void> {
    this.callbacks = callbacks;

    return new Promise((resolve, reject) => {
      try {
        this.ws = new WebSocket(`${this.baseUrl}/api/ws/chat`);

        this.ws.onopen = () => {
          this.reconnectAttempts = 0;
          resolve();
        };

        this.ws.onmessage = (event) => {
          try {
            const parsed = JSON.parse(event.data);
            handleStreamEvent(parsed, this.callbacks);
          } catch {
            // Ignore malformed messages
          }
        };

        this.ws.onclose = () => {
          this.handleDisconnect();
        };

        this.ws.onerror = (error) => {
          console.error('WebSocket error:', error);
          reject(error);
        };
      } catch (error) {
        reject(error);
      }
    });
  }

  send(messages: ChatRequest['messages'], model?: string): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ messages, model }));
    } else {
      console.error('WebSocket not connected');
    }
  }

  private handleDisconnect(): void {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);
      console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);
      setTimeout(() => this.connect(this.callbacks), delay);
    } else {
      this.callbacks.onError?.('WebSocket connection lost');
    }
  }

  disconnect(): void {
    this.reconnectAttempts = this.maxReconnectAttempts; // Prevent reconnect
    this.ws?.close();
    this.ws = null;
  }

  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}