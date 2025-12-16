import { NextRequest, NextResponse } from 'next/server';

/**
 * Apriel 1.6 Chat API Route
 * =========================
 * Works with your EXISTING backend config - no model name changes.
 * Just simplified streaming for the SFT-trained 1.6 model.
 */

export async function POST(req: NextRequest) {
  try {
    const { messages, model } = await req.json();

    // Use your existing backend exactly as configured
    const upstreamUrl = process.env.AETHER_UPSTREAM_URL || 'http://localhost:8001/v1/chat/completions';
    const apiKey = process.env.AETHER_API_KEY || 'sk-aether-sovereign-master-key-2026';

    const upstreamResponse = await fetch(upstreamUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${apiKey}`,
      },
      body: JSON.stringify({
        model: model || 'apriel',  // Uses whatever model name your backend expects
        messages: messages,
        temperature: 0.7,
        top_p: 0.9,
        max_tokens: 8192,
        stream: true,
      }),
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

    // Simple streaming - no complex parsing for 1.6
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
                  emit({ type: 'finish', reason: json.choices[0].finish_reason });
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