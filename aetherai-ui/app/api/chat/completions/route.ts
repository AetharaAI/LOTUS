import { NextRequest, NextResponse } from 'next/server';

/**
 * Apriel 1.6 Chat API Route
 * =========================
 * Clean OpenAI-compatible streaming for SFT-trained model.
 * No custom parsing needed - model outputs standard format.
 */

const API_URL = '/api';

// Optional: If you want to inject a system prompt
const SYSTEM_PROMPT = `You are Apriel, a helpful AI assistant. You provide clear, accurate, and thoughtful responses.`;

// Tool definitions (if using function calling)
const TOOLS = [
  {
    type: 'function',
    function: {
      name: 'web_search',
      description: 'Search the web for current information',
      parameters: {
        type: 'object',
        properties: {
          query: {
            type: 'string',
            description: 'The search query'
          }
        },
        required: ['query']
      }
    }
  }
];

export async function POST(req: NextRequest) {
  try {
    const { messages, model = 'apriel' } = await req.json();

    // Optionally inject system prompt if not already present
    const hasSystemPrompt = messages.some((m: any) => m.role === 'system');
    const fullMessages = hasSystemPrompt 
      ? messages 
      : [{ role: 'system', content: SYSTEM_PROMPT }, ...messages];

    // Your vLLM + LiteLLM endpoint
    const upstreamUrl = process.env.AETHER_UPSTREAM_URL || 'http://localhost:8001/v1/chat/completions';

    const upstreamResponse = await fetch(upstreamUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${process.env.AETHER_API_KEY || 'sk-aether-sovereign-master-key-2026'}`,
      },
      body: JSON.stringify({
        model: model,
        messages: fullMessages,
        // Apriel 1.6 optimal parameters
        temperature: 0.7,
        top_p: 0.9,
        max_tokens: 8192,
        stream: true,
        // Enable if you want function calling
        // tools: TOOLS,
        // tool_choice: 'auto',
      }),
      signal: AbortSignal.timeout(600000), 
    });

    if (!upstreamResponse.ok) {
      const errText = await upstreamResponse.text();
      console.error('Upstream Error:', errText);
      throw new Error(`Upstream Error: ${upstreamResponse.status} - ${errText}`);
    }

    const encoder = new TextEncoder();
    const decoder = new TextDecoder();

    // Simple pass-through stream - no parsing needed for SFT model
    const stream = new ReadableStream({
      async start(controller) {
        const emit = (payload: object) => {
          controller.enqueue(encoder.encode(`data: ${JSON.stringify(payload)}\n\n`));
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
                  // Handle tool calls if enabled
                  if (delta.tool_calls) {
                    // Accumulate tool call
                    emit({ 
                      type: 'tool_call', 
                      tool_call: delta.tool_calls[0] 
                    });
                    continue;
                  }

                  // Handle regular content
                  if (delta.content) {
                    emit({ 
                      type: 'content', 
                      content: delta.content 
                    });
                  }
                }

                // Handle finish reason
                if (json.choices?.[0]?.finish_reason) {
                  emit({ 
                    type: 'finish', 
                    reason: json.choices[0].finish_reason 
                  });
                }

              } catch (e) {
                // Ignore parse errors
                console.error('Parse error:', e);
              }
            }
          }

          controller.enqueue(encoder.encode('data: [DONE]\n\n'));
          controller.close();

        } catch (error) {
          console.error('Stream error:', error);
          emit({ type: 'error', error: String(error) });
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
    console.error('API Route Error:', error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}