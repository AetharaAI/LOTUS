/**
 * Enterprise SSE Streaming Client for Apriel 1.6
 * ===============================================
 * Production-grade streaming for AetherPro.tech
 * Maintains full API compatibility with existing ChatInterface.tsx
 */

const API_URL = '/api';

export interface StreamCallbacks {
  // Thinking events (Apriel 1.6 doesn't use these, but keeping for compatibility)
  onThinkingStart?: () => void;
  onThinking?: (chunk: string) => void;
  onThinkingEnd?: (fullThinking: string) => void;

  // Content events
  onContent?: (chunk: string) => void;
  onFinalStart?: () => void;
  onFinalResponse?: (response: string) => void;

  // Tool events (for future use)
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
 * Handle individual stream events
 * Updated to support both Apriel custom events AND standard OpenAI/vLLM chunks
 */
function handleStreamEvent(parsed: any, callbacks: StreamCallbacks): void {
  // === 1. Standard OpenAI/vLLM Support ===
  // vLLM sends { choices: [{ delta: { content: "..." } }] }
  if (parsed.choices?.[0]?.delta?.content) {
    callbacks.onContent?.(parsed.choices[0].delta.content);
    return;
  }

  // Handle OpenAI [DONE] or empty deltas if needed
  if (parsed.choices?.[0]?.finish_reason) {
    return;
  }

  // Handle OpenAI-style tool_calls in delta (vLLM/Qwen with tools enabled)
  if (parsed.choices?.[0]?.delta?.tool_calls) {
    callbacks.onToolCallsDetected?.(parsed.choices[0].delta.tool_calls);
    return;
  }

  // === 2. Custom Apriel Protocol ===
  const eventType = parsed.type;

  switch (eventType) {
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

    case 'model':
      callbacks.onModel?.(parsed.model, parsed.tokens_used);
      break;

    case 'error':
      callbacks.onError?.(parsed.error || parsed.message || 'Unknown error');
      break;

    case 'done':
      callbacks.onDone?.(parsed.response);
      break;

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

    default:
      if (!parsed.choices) {
        console.debug('Unknown stream event:', eventType, parsed);
      }
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