/**
 * Universal SSE Streaming Client
 * Handles: OpenAI format, vLLM format, Apriel format, LiteLLM format
 * Production-grade error handling
 */

const API_URL = '/api';

export interface StreamCallbacks {
  // Thinking events (Apriel legacy)
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
        enable_tools: request.enable_tools ?? false,
      }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      const errorMsg = errorData.error || errorData.detail || `HTTP ${response.status}`;
      console.error('[StreamChat] API Error:', errorMsg, errorData);
      throw new Error(errorMsg);
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

      // Process complete SSE events (separated by \n\n)
      const events = buffer.split('\n\n');
      buffer = events.pop() || '';

      for (const event of events) {
        if (!event.trim()) continue;

        const lines = event.split('\n');
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.substring(6).trim();

            if (data === '[DONE]') {
              callbacks.onDone?.();
              return;
            }

            try {
              const parsed = JSON.parse(data);
              handleStreamEvent(parsed, callbacks);
            } catch (e) {
              // Silently skip malformed JSON (common in SSE)
              console.debug('[StreamChat] Skipped malformed chunk:', data.slice(0, 100));
            }
          }
        }
      }
    }
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Unknown streaming error';
    console.error('[StreamChat] Fatal error:', errorMessage);
    callbacks.onError?.(errorMessage);
  }
}

/**
 * Universal event handler - supports multiple streaming formats
 */
function handleStreamEvent(parsed: any, callbacks: StreamCallbacks): void {
  // Format 1: OpenAI/vLLM standard format
  if (parsed.choices && Array.isArray(parsed.choices) && parsed.choices.length > 0) {
    const choice = parsed.choices[0];
    const delta = choice.delta;

    // Content chunk
    if (delta?.content) {
      callbacks.onContent?.(delta.content);
      return;
    }

    // Tool calls
    if (delta?.tool_calls) {
      callbacks.onToolCallsDetected?.(delta.tool_calls);
      return;
    }

    // Finish reason
    if (choice.finish_reason) {
      // Stream complete
      return;
    }
  }

  // Format 2: Direct content (some vLLM configs)
  if (parsed.content && typeof parsed.content === 'string') {
    callbacks.onContent?.(parsed.content);
    return;
  }

  // Format 3: Apriel legacy thinking format
  if (parsed.type === 'thinking' && parsed.content) {
    callbacks.onThinking?.(parsed.content);
    return;
  }

  // Format 4: Apriel legacy response format
  if (parsed.type === 'response' && parsed.content) {
    callbacks.onContent?.(parsed.content);
    return;
  }

  // Format 5: Tool results (custom)
  if (parsed.type === 'tool_result') {
    callbacks.onToolResult?.({
      tool: parsed.tool,
      query: parsed.query || '',
      results: parsed.results || [],
      status: 'complete',
    });
    return;
  }

  // Format 6: Tool errors (custom)
  if (parsed.type === 'tool_error') {
    callbacks.onToolError?.(parsed.tool, parsed.error || 'Tool execution failed');
    return;
  }

  // Format 7: Error objects
  if (parsed.error) {
    const errorMsg = typeof parsed.error === 'string' 
      ? parsed.error 
      : parsed.error.message || 'Stream error';
    callbacks.onError?.(errorMsg);
    return;
  }

  // Format 8: LiteLLM metadata
  if (parsed.model) {
    callbacks.onModel?.(parsed.model, parsed.usage?.total_tokens);
    return;
  }

  // Unknown format - log but don't crash
  console.debug('[StreamChat] Unhandled event type:', parsed.type || 'unknown', parsed);
}

/**
 * Non-streaming fallback
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

  const result = await response.json();

  // Handle OpenAI format
  if (result.choices?.[0]?.message) {
    return {
      content: result.choices[0].message.content || '',
      model: result.model || 'unknown',
      tool_calls: result.choices[0].message.tool_calls,
    };
  }

  // Handle direct format
  return result;
}