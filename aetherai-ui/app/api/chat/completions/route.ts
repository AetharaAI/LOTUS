import { NextRequest } from 'next/server';

const SYSTEM_PROMPT = `You are AetherAI, the sovereign assistant of AetherPro Technologies.

You run on a fully self-hosted, sovereign stack (OVHcloud GPUs, AetherAuth, Triad Intelligence).
Your job:
- Be direct, high-signal, and technically precise.
- Prioritize sovereign, self-hostable solutions (Docker, Postgres, Redis/Valkey, Weaviate, vLLM, etc.).
- Assume the user is an advanced builder working on infra, agents, and skilled trades.

Style:
- Use clear, modern engineering language.
- Prefer concise explanations with bullet points or short sections.
- When you are unsure about a detail, say so instead of hallucinating.`;

export const runtime = 'nodejs';

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { messages = [], model, temperature } = body;

    const fullMessages = [
      { role: 'system', content: SYSTEM_PROMPT },
      ...messages,
    ];

    // 1. Define the base hostname/port for LiteLLM.
    // Change env var name to reflect it is just the base.
    // Default to common local LiteLLM port if unset.
    let upstreamBase = process.env.AETHER_LITELLM_BASE_URL || 'http://api.aetherpro.tech:8001';

    // 2. Remove trailing slash if present to ensure clean append.
    if (upstreamBase.endsWith('/')) {
        upstreamBase = upstreamBase.slice(0, -1);
    }

    // 3. Construct the full validated endpoint.
    const upstreamUrl = `${upstreamBase}/v1/chat/completions`;

    // Debug log to confirm traffic flow in server console
    console.log(`[Aether API] Proxying request to: ${upstreamUrl}`);

    const upstreamResponse = await fetch(upstreamUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${process.env.AETHER_API_KEY ?? ''}`,
      },
      body: JSON.stringify({
        model: model || 'qwen3-vl-local',
        messages: fullMessages,
        temperature: temperature ?? 0.7,
        max_tokens: 2048,
        top_p: 0.95,
        stream: true,
      }),
      signal: AbortSignal.timeout(600000),
    });

    if (!upstreamResponse.ok || !upstreamResponse.body) {
      const errText = await upstreamResponse.text().catch(() => '');
      console.error(
        'LiteLLM upstream error:',
        upstreamResponse.status,
        errText
      );
      return new Response(
        JSON.stringify({
          error: `LiteLLM error ${upstreamResponse.status}`,
          detail: errText,
        }),
        { status: 500, headers: { 'Content-Type': 'application/json' } }
      );
    }

    const stream = new ReadableStream({
      async start(controller) {
        const reader = upstreamResponse.body!.getReader();
        try {
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            if (value) controller.enqueue(value);
          }
        } catch (e) {
          console.error('Stream error:', e);
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
  } catch (err: any) {
    console.error('Chat route fatal error:', err);
    return new Response(
      JSON.stringify({
        error: err?.message || 'Unknown error in /api/chat',
      }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    );
  }
}
