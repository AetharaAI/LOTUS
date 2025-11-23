##  Old route.ts that worked:
import { NextRequest, NextResponse } from 'next/server';

// THE SYSTEM PROMPT (The Governor)
const SYSTEM_PROMPT = `
You are Apriel, Sovereign AI of AetherPro. 
- ROLE: Master Electrician & Enterprise Architect.
- MODE: Thinking Mode Enabled.
- OUTPUT: Use <think> tags for reasoning, then output the final answer.
`;

export async function POST(req: NextRequest) {
  try {
    const { messages, model, temperature } = await req.json();

    // 1. Inject the System Prompt
    const fullMessages = [
      { role: 'system', content: SYSTEM_PROMPT },
      ...messages
    ];

    // 2. Open the connection to the L40S (vLLM)
    const upstreamResponse = await fetch(process.env.AETHER_UPSTREAM_URL!, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${process.env.AETHER_API_KEY}`,
      },
      body: JSON.stringify({
        model: model || 'apriel-1.5-15b-thinker',
        messages: fullMessages,
        temperature: temperature || 0.3,
        stream: true, // Vital: We need the raw stream
        max_tokens: 8192,
      }),
    });

    if (!upstreamResponse.ok) {
      throw new Error(`L40S Error: ${upstreamResponse.statusText}`);
    }

    // 3. Create the Transcoder Stream
    const encoder = new TextEncoder();
    const decoder = new TextDecoder();

    const stream = new ReadableStream({
      async start(controller) {
        const reader = upstreamResponse.body?.getReader();
        if (!reader) return controller.close();

        let buffer = '';
        let isThinking = false;

        try {
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value, { stream: true });
            
            // vLLM sends: data: { JSON } \n\n
            const lines = chunk.split('\n');

            for (const line of lines) {
              if (line.startsWith('data: ') && line !== 'data: [DONE]') {
                try {
                  const json = JSON.parse(line.slice(6));
                  const content = json.choices[0]?.delta?.content || '';

                  if (!content) continue;

                  // --- THE PARSING LOGIC ---
                  
                  // Check for Start of Thought
                  if (content.includes('<think>')) {
                    isThinking = true;
                    const clean = content.replace('<think>', '');
                    if (clean) {
                      // Send "Thinking" event
                      const payload = JSON.stringify({ type: 'thinking', content: clean });
                      controller.enqueue(encoder.encode(`data: ${payload}\n\n`));
                    }
                    continue;
                  }

                  // Check for End of Thought
                  if (content.includes('</think>')) {
                    isThinking = false;
                    const clean = content.replace('</think>', '');
                    if (clean) {
                      // Switch back to "Content" event
                      const payload = JSON.stringify({ type: 'content', content: clean });
                      controller.enqueue(encoder.encode(`data: ${payload}\n\n`));
                    }
                    continue;
                  }

                  // Normal Streaming
                  const type = isThinking ? 'thinking' : 'content';
                  const payload = JSON.stringify({ type, content });
                  controller.enqueue(encoder.encode(`data: ${payload}\n\n`));

                } catch (e) {
                  // Ignore parse errors on partial chunks
                }
              }
            }
          }
          
          // 4. Send [DONE] signal expected by your library
          controller.enqueue(encoder.encode('data: [DONE]\n\n'));
          controller.close();

        } catch (error) {
          const errPayload = JSON.stringify({ type: 'error', error: 'Stream Failed' });
          controller.enqueue(encoder.encode(`data: ${errPayload}\n\n`));
          controller.close();
        }
      },
    });

    return new NextResponse(stream, {
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
      },
    });

  } catch (error: any) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}

##  Old streaming.ts that worked before adding tools:

/**
 * SSE Streaming Client
 *
 * Handles Server-Sent Events for real-time chat streaming.
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://aetherpro.tech';

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
      body: JSON.stringify({
        ...request,
        stream: true,
      }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
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
  const response = await fetch(`${API_URL}/api/chat/completions`, {
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
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
}

