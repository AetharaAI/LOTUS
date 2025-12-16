/**
 * SSE Streaming Client for Apriel 1.6
 * ====================================
 * Clean streaming for SFT-trained model.
 * No complex parsing - standard OpenAI format.
 */

const API_URL = '/api/chat';

export interface StreamCallbacks {
  onContent?: (content: string) => void;
  onToolCall?: (toolCall: any) => void;
  onFinish?: (reason: string) => void;
  onError?: (error: string) => void;
}

export async function streamChat(
  messages: Array<{ role: string; content: string }>,
  model: string = 'apriel',
  callbacks: StreamCallbacks = {}
) {
  const response = await fetch(API_URL, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ messages, model }),
  });

  if (!response.ok) {
    const error = await response.text();
    callbacks.onError?.(error);
    throw new Error(`API Error: ${response.status} - ${error}`);
  }

  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error('No response body');
  }

  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || ''; // Keep incomplete line in buffer

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        if (line === 'data: [DONE]') continue;

        try {
          const data = JSON.parse(line.slice(6));

          switch (data.type) {
            case 'content':
              callbacks.onContent?.(data.content);
              break;

            case 'tool_call':
              callbacks.onToolCall?.(data.tool_call);
              break;

            case 'finish':
              callbacks.onFinish?.(data.reason);
              break;

            case 'error':
              callbacks.onError?.(data.error);
              break;
          }
        } catch (e) {
          console.error('Parse error:', e);
        }
      }
    }
  } catch (error) {
    callbacks.onError?.(String(error));
    throw error;
  }
}

// React hook for easy integration
export function useStreamChat() {
  const [isStreaming, setIsStreaming] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const sendMessage = async (
    messages: Array<{ role: string; content: string }>,
    model: string = 'apriel',
    callbacks: StreamCallbacks = {}
  ) => {
    setIsStreaming(true);
    setError(null);

    try {
      await streamChat(messages, model, {
        ...callbacks,
        onError: (err) => {
          setError(err);
          callbacks.onError?.(err);
        },
        onFinish: (reason) => {
          setIsStreaming(false);
          callbacks.onFinish?.(reason);
        },
      });
    } catch (err) {
      setIsStreaming(false);
      setError(String(err));
    }
  };

  return { sendMessage, isStreaming, error };
}