import { NextRequest, NextResponse } from 'next/server';

const SYSTEM_PROMPT = `You are Aether, also known as AetherAI, the sovereign AI assistant for AetherPro Technologies.

ROLE:
- Senior technical advisor and AI architect for sovereign, self-hosted infrastructure.
- You help design, debug, and deploy systems across AI, infra, and trades.

STYLE:
- Direct, high-signal, no fluff.
- Prefer concrete steps: commands, config snippets, file paths.
- Explain assumptions if something is ambiguous, but stay concise.

GUIDELINES:
- Favor sovereign, self-hosted, privacy-preserving solutions over SaaS.
- When code or commands are risky, call it out explicitly.
- Use short sections and bullet points when it improves clarity.

FORMAT:
- Respond in normal natural language. Do NOT wrap reasoning in <think> tags.
- You do not need special markers like [BEGIN FINAL RESPONSE].
- When you call tools, keep arguments minimal and precise.`;

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
    const { messages, model, enable_tools } = await req.json();

    // Simple model selection - frontend picks the backend
    const clientModel = (model as string | undefined) ?? 'qwen3-vl-local';

    const fullMessages = [
      { role: 'system', content: SYSTEM_PROMPT },
      ...messages,
    ];

    const useTools = enable_tools !== false; // default true if not provided

    // Choose backend URL based on model
    let upstreamUrl: string;
    let apiKey: string;

    if (clientModel === 'qwen3-vl-local') {
      // Build upstream URL - handle both base URL and full path in env var
      const envUrl = process.env.AETHER_UPSTREAM_URL || 'http://localhost:8000/v1/chat/completions';

      if (envUrl.includes('/chat/completions')) {
        // Env var already has the full path
        upstreamUrl = envUrl.replace(/\/$/, '');
      } else {
        // Env var is just the base URL
        const baseUrl = envUrl.replace(/\/$/, '');
        upstreamUrl = `${baseUrl}/v1/chat/completions`;
      }

      apiKey = process.env.AETHER_API_KEY!;
    } else if (clientModel === 'qwen3-omni-remote') {
      upstreamUrl = 'https://api.blackboxaudio.tech/v1/chat/completions';
      apiKey = process.env.BLACKBOX_API_KEY || 'sk-blackbox-omni';
    } else {
      // Default to local
      const envUrl = process.env.AETHER_UPSTREAM_URL || 'http://localhost:8000/v1/chat/completions';

      if (envUrl.includes('/chat/completions')) {
        upstreamUrl = envUrl.replace(/\/$/, '');
      } else {
        const baseUrl = envUrl.replace(/\/$/, '');
        upstreamUrl = `${baseUrl}/v1/chat/completions`;
      }

      apiKey = process.env.AETHER_API_KEY!;
    }

    const upstreamResponse = await fetch(upstreamUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${apiKey}`,
      },
      body: JSON.stringify({
        model: clientModel,
        messages: fullMessages,
        temperature: 0.6,
        repetition_penalty: 1.0,
        max_tokens: 8192,
        top_p: 0.95,
        stream: true,
        ...(useTools && { tools: TOOLS, tool_choice: 'auto' }),
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
