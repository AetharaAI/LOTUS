/**
 * SSE Streaming Client
 *
 * Handles Server-Sent Events for real-time chat streaming.
 * Routes through Next.js API route for secure authentication.
 */

const API_URL = '/api';

export interface StreamCallbacks {
  onThinking?: (thinking: string) => void;
  onContent?: (chunk: string) => void;
  onModel?: (model: string, tokensUsed?: number) => void;
  onError?: (error: string) => void;
  onDone?: () => void;
}

export interface ChatRequest {
  messages: Array<{ role: string; content: string }>;
  model?: string;
  temperature?: number;
  max_tokens?: number;
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
      body: JSON.stringify(request),
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
            } catch (e) {
              console.error('Failed to parse SSE data:', e);
            }
          }
        }
      }
    }
  } catch (error) {
    const errorMessage =
      error instanceof Error ? error.message : 'Unknown error';
    callbacks.onError?.(errorMessage);
  }
}

/**
 * Simple non-streaming chat completion (fallback)
 */
export async function chatCompletion(
  request: ChatRequest
): Promise<{ content: string; model: string }> {
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
