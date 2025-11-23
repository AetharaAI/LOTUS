import { NextRequest, NextResponse } from 'next/server';

const SYSTEM_PROMPT = `You are Apriel, Sovereign AI of AetherPro Technologies.

CRITICAL RESPONSE RULES:
- Maximum 300 words per response (unless user explicitly requests more detail)
- Lead with direct answer in 1-2 sentences
- Use 2-3 bullet points maximum for key details
- NO tables, charts, or extensive formatting by default
- Be conversational, not academic

ROLE: Technical advisor and AI architect for sovereign infrastructure

TONE: Professional senior engineer giving a quick briefing

TOOL USAGE:
- You have access to web_search for current information
- Use ONLY when query requires recent data or facts beyond your training
- Always cite sources when using search results

RESPONSE STRUCTURE:
1. Direct answer (1-2 sentences)
2. Key supporting points (2-3 bullets if needed)
3. Offer to elaborate: "Need more detail on anything?"

GOOD EXAMPLE:
"You'd need an RTX 3060 Ti minimum (8GB VRAM) for that pipeline. Gives you ~15 TFLOPs which handles vision + audio + voice at 1080p/30fps. Want specifics on any component?"

BAD EXAMPLE:
[Long tables, extensive calculations, multiple sections, step-by-step breakdowns without being asked]

When thinking through complex problems:
- Break reasoning into clear steps (use "Step 1:", "Next:", "Therefore:")
- Keep each thinking step to 1-2 sentences
- Conclude thinking before providing final answer`;

// Tool definitions for Apriel
const TOOLS = [
  {
    type: 'function',
    function: {
      name: 'web_search',
      description: 'Search the web for current information, recent news, or facts not in training data. Use when the user asks about current events, recent developments, or specific information you don\'t have.',
      parameters: {
        type: 'object',
        properties: {
          query: {
            type: 'string',
            description: 'The search query. Be specific and concise. Example: "latest AI infrastructure trends 2025"',
          },
          num_results: {
            type: 'integer',
            description: 'Number of results to return (1-10). Default is 5.',
            default: 5,
            minimum: 1,
            maximum: 10,
          },
        },
        required: ['query'],
      },
    },
  },
];

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
        temperature: 0.7,
        repetition_penalty: 1.25,      // Increased to kill "We can also mention" loops
        max_tokens: 600,                // Reduced to force brevity (~450 words)
        top_p: 0.92,                    // Added to reduce unlikely tokens
        frequency_penalty: 0.2,         // Penalizes word repetition
        presence_penalty: 0.1,          // Encourages topic diversity
        stream: true,
        tools: TOOLS,                   // Tool definitions
        tool_choice: 'auto',            // Let model decide when to search
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

                  // Handle tool calls
                  if (json.choices[0]?.delta?.tool_calls) {
                    const toolCall = json.choices[0].delta.tool_calls[0];

                    if (toolCall?.function?.name === 'web_search') {
                      try {
                        // Parse tool arguments
                        const args = JSON.parse(toolCall.function.arguments || '{}');

                        // Emit tool use start event
                        const toolStartPayload = JSON.stringify({
                          type: 'tool_use',
                          tool: 'web_search',
                          query: args.query,
                          status: 'searching',
                        });
                        controller.enqueue(encoder.encode(`data: ${toolStartPayload}\n\n`));

                        // Call our search API
                        const searchResponse = await fetch('http://localhost:3000/api/search', {
                          method: 'POST',
                          headers: { 'Content-Type': 'application/json' },
                          body: JSON.stringify({
                            query: args.query,
                            num_results: args.num_results || 5,
                          }),
                        });

                        if (searchResponse.ok) {
                          const searchData = await searchResponse.json();

                          // Emit search results
                          const toolResultPayload = JSON.stringify({
                            type: 'tool_result',
                            tool: 'web_search',
                            query: args.query,
                            results: searchData.results || [],
                            status: 'complete',
                          });
                          controller.enqueue(encoder.encode(`data: ${toolResultPayload}\n\n`));
                        } else {
                          // Emit error
                          const toolErrorPayload = JSON.stringify({
                            type: 'tool_error',
                            tool: 'web_search',
                            error: 'Search failed',
                          });
                          controller.enqueue(encoder.encode(`data: ${toolErrorPayload}\n\n`));
                        }
                      } catch (e) {
                        console.error('Tool call error:', e);
                      }
                    }
                    continue;
                  }

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