import { NextRequest } from 'next/server';

const SYSTEM_PROMPT = `You are AetherAI, the sovereign assistant of AetherPro Technologies.

You run on a fully self-hosted, sovereign stack (OVHcloud, AetherAuth, Triad Intelligence).
Your job:
- Be direct, high-signal, and technically precise.
- Prioritize sovereign, self-hostable solutions (Docker, Postgres, Redis/Valkey, Weaviate, vLLM, etc.).
- Assume the user is an advanced builder working on infra, agents, and skilled trades.

Style:
- Use clear, modern engineering language.
- Prefer concise explanations with bullet points or short sections.
- When you are unsure about a detail, say so instead of hallucinating.

Do NOT wrap your reasoning in special tags; just answer in normal markdown.`;

const TOOLS = [
  {
    type: 'function',
    function: {
      name: 'web_search',
      description:
        'Search the web for current information, recent news, or facts not in training data.',
      parameters: {
        type: 'object',
        properties: {
          query: {
            type: 'string',
            description: 'The search query. Be specific and concise.',
          },
          num_results: {
            type: 'integer',
            description: 'Number of results to return (1-10). Default is 5.',
            default: 5,
          },
        },
        required: ['query'],
      },
    },
  },
];

export const runtime = 'nodejs';

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { messages = [], model, temperature, enable_tools } = body;

    const fullMessages = [
      { role: 'system', content: SYSTEM_PROMPT },
      ...messages,
    ];

    // Build upstream URL - handle both base URL and full path in env var
    const envUrl = process.env.AETHER_UPSTREAM_URL || 'http://localhost:8000/v1/chat/completions';
    let upstreamUrl: string;

    if (envUrl.includes('/chat/completions')) {
      // Env var already has the full path
      upstreamUrl = envUrl.replace(/\/$/, '');
    } else {
      // Env var is just the base URL
      const baseUrl = envUrl.replace(/\/$/, '');
      upstreamUrl = `${baseUrl}/v1/chat/completions`;
    }

    const upstreamResponse = await fetch(upstreamUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${
          process.env.AETHER_API_KEY ||
          'sk-aether-sovereign-master-key-2026'
        }`,
      },
      body: JSON.stringify({
        model: model || 'qwen3-vl-local',
        messages: fullMessages,
        temperature: temperature ?? 0.7,
        max_tokens: 8192,
        top_p: 0.95,
        stream: true,
        // tools are wired through but not executed server-side (yet)
        tools: enable_tools ? TOOLS : undefined,
        tool_choice: enable_tools ? 'auto' : 'none',
      }),
      // be generous; GPU cold starts happen
      signal: AbortSignal.timeout(600000),
    });

    if (!upstreamResponse.ok || !upstreamResponse.body) {
      const errText = await upstreamResponse.text().catch(() => '');
      console.error('Upstream Error:', upstreamResponse.status, errText);
      return new Response(
        JSON.stringify({
          error: `Upstream Error: ${upstreamResponse.status}`,
        }),
        { status: 500, headers: { 'Content-Type': 'application/json' } }
      );
    }

    // Just stream LiteLLM / vLLM output straight through as SSE
    const stream = new ReadableStream({
      async start(controller) {
        const reader = upstreamResponse.body!.getReader();
        const encoder = new TextEncoder();

        try {
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            if (value) {
              controller.enqueue(value);
            }
          }
        } catch (err) {
          console.error('Stream error:', err);
        } finally {
          controller.close();
        }
      },
    });

    return new Response(stream, {
      status: 200,
      headers: {
        'Content-Type': 'text/event-stream; charset=utf-8',
        'Cache-Control': 'no-cache, no-transform',
        Connection: 'keep-alive',
        'Transfer-Encoding': 'chunked',
      },
    });
  } catch (error: any) {
    console.error('Chat route error:', error);
    return new Response(
      JSON.stringify({ error: error?.message || 'Unknown error' }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    );
  }
}
