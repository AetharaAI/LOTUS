import { NextRequest, NextResponse } from 'next/server';

// 1. THE CLEAN SYSTEM PROMPT
// We removed the instructions about <think> tags because the model does that natively.
// We removed the "Deconstruct problems" instruction because it causes meta-analysis.
const SYSTEM_PROMPT = `
You are Apriel, Sovereign AI of AetherPro.
ROLE: Enterprise Architect for Sovereign AI.
TONE: Professional, Astute, Concise.
INSTRUCTION: Provide assistance to Sovereign AI Enterprise and answer general inquiries to any questions including non-domain topics.
`;

export async function POST(req: NextRequest) {
  try {
    const { messages, model } = await req.json();

    // Inject System Prompt
    const fullMessages = [
      { role: 'system', content: SYSTEM_PROMPT },
      ...messages
    ];

    const upstreamResponse = await fetch(process.env.AETHER_UPSTREAM_URL!, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${process.env.AETHER_API_KEY}`,
      },
      body: JSON.stringify({
        model: model || 'apriel-1.5-15b-thinker',
        messages: fullMessages,
        // 2. TUNING PARAMETERS
        temperature: 0.6,         // Increased from 0.3 to prevent loops
        repetition_penalty: 1.1,  // CRITICAL: Kills the "We can also mention" loop
        max_tokens: 4096,         // Cap the output so it doesn't ramble
        stream: true,
      }),
    });

    if (!upstreamResponse.ok) {
      const errText = await upstreamResponse.text();
      console.error("L40S Error:", errText);
      throw new Error(`L40S Error: ${upstreamResponse.status} ${upstreamResponse.statusText}`);
    }

    const encoder = new TextEncoder();
    const decoder = new TextDecoder();

    const stream = new ReadableStream({
      async start(controller) {
        const reader = upstreamResponse.body?.getReader();
        if (!reader) return controller.close();

        let isThinking = false;

        try {
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value, { stream: true });
            const lines = chunk.split('\n');

            for (const line of lines) {
              if (line.startsWith('data: ') && line !== 'data: [DONE]') {
                try {
                  const json = JSON.parse(line.slice(6));
                  const content = json.choices[0]?.delta?.content || '';

                  if (!content) continue;

                  // 3. ROBUST TAG PARSING
                  // Sometimes the model outputs "<think>\n" split across chunks.
                  
                  if (content.includes('<think>')) {
                    isThinking = true;
                    const clean = content.replace('<think>', '');
                    if (clean.trim()) {
                      const payload = JSON.stringify({ type: 'thinking', content: clean });
                      controller.enqueue(encoder.encode(`data: ${payload}\n\n`));
                    }
                    continue;
                  }

                  if (content.includes('</think>')) {
                    isThinking = false;
                    const clean = content.replace('</think>', '');
                    if (clean.trim()) {
                      const payload = JSON.stringify({ type: 'content', content: clean });
                      controller.enqueue(encoder.encode(`data: ${payload}\n\n`));
                    }
                    continue;
                  }

                  const type = isThinking ? 'thinking' : 'content';
                  const payload = JSON.stringify({ type, content });
                  controller.enqueue(encoder.encode(`data: ${payload}\n\n`));

                } catch (e) {
                   // Ignore partial JSON chunks
                }
              }
            }
          }
          controller.enqueue(encoder.encode('data: [DONE]\n\n'));
          controller.close();
        } catch (error) {
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