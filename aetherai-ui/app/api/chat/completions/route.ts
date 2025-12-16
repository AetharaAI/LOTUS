import { NextRequest, NextResponse } from 'next/server';

/**
 * Enterprise Apriel 1.6 Chat API Route
 * ====================================
 * Production-grade streaming for AetherPro.tech
 * Works with existing ChatInterface.tsx signature
 */

// Tool definitions for web_search
const TOOLS = [
  {
    type: 'function',
    function: {
      name: 'web_search',
      description: 'Search the web for current information',
      parameters: {
        type: 'object',
        properties: {
          query: { type: 'string', description: 'Search query' }
        },
        required: ['query']
      }
    }
  }
];

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { messages, model, temperature, max_tokens, enable_tools } = body;

    // Your production backend
    const upstreamUrl = process.env.AETHER_UPSTREAM_URL || 'http://localhost:8001/v1/chat/completions';
    const apiKey = process.env.AETHER_API_KEY || 'sk-aether-sovereign-master-key-2026';

    const requestBody: any = {
      model: model || 'apriel',
      messages: messages,
      temperature: temperature || 0.7,
      max_tokens: max_tokens || 8192,
      stream: true,
    };

    // Add tools if enabled
    if (enable_tools) {
      requestBody.tools = TOOLS;
      requestBody.tool_choice = 'auto';
    }

    const upstreamResponse = await fetch(upstreamUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${apiKey}`,
      },
      body: JSON.stringify(requestBody),
      signal: AbortSignal.timeout(600000),
    });

    if (!upstreamResponse.ok) {
      const errText = await upstreamResponse.text();
      console.error('Upstream Error:', errText);
      return NextResponse.json(
        { error: `Upstream Error: ${upstreamResponse.status}` },
        { status: upstreamResponse.status }
      );
    }

    const encoder = new TextEncoder();
    const decoder = new TextDecoder();

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

                if (delta?.content) {
                  emit({ type: 'content', content: delta.content });
                }

                if (json.choices?.[0]?.finish_reason) {
                  emit({ type: 'done', reason: json.choices[0].finish_reason });
                }
              } catch (e) {
                // Ignore parse errors
              }
            }
          }

          emit({ type: 'done' });
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