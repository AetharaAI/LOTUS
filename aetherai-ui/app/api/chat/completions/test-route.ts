import { NextRequest, NextResponse } from 'next/server';

/**
 * Diagnostic endpoint: /api/chat/test
 * Tests LiteLLM connectivity without streaming complexity
 */
export async function GET(req: NextRequest) {
  const upstreamBase = process.env.AETHER_UPSTREAM_URL || 
                       process.env.UPSTREAM_URL || 
                       process.env.LITELLM_URL || 
                       'http://localhost:8001';

  const upstreamUrl = `${upstreamBase.replace(/\/$/, '')}/v1/models`;

  console.log('[Test] Checking LiteLLM at:', upstreamUrl);

  try {
    const response = await fetch(upstreamUrl, {
      headers: {
        Authorization: `Bearer ${process.env.AETHER_API_KEY ?? ''}`,
      },
    });

    const data = await response.json();

    return NextResponse.json({
      status: 'ok',
      upstream: upstreamUrl,
      statusCode: response.status,
      models: data.data || data,
    });
  } catch (err: any) {
    console.error('[Test] Failed:', err.message);
    return NextResponse.json({
      status: 'error',
      upstream: upstreamUrl,
      error: err.message,
    }, { status: 500 });
  }
}

export async function POST(req: NextRequest) {
  const upstreamBase = process.env.AETHER_UPSTREAM_URL || 
                       process.env.UPSTREAM_URL || 
                       process.env.LITELLM_URL || 
                       'http://localhost:8001';

  const upstreamUrl = `${upstreamBase.replace(/\/$/, '')}/v1/chat/completions`;

  console.log('[Test] Sending test message to:', upstreamUrl);

  try {
    const response = await fetch(upstreamUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${process.env.AETHER_API_KEY ?? ''}`,
      },
      body: JSON.stringify({
        model: 'qwen3-vl-local',
        messages: [{ role: 'user', content: 'Say "test successful"' }],
        max_tokens: 50,
        stream: false,
      }),
    });

    const data = await response.json();

    return NextResponse.json({
      status: 'ok',
      upstream: upstreamUrl,
      statusCode: response.status,
      response: data,
    });
  } catch (err: any) {
    console.error('[Test] Failed:', err.message);
    return NextResponse.json({
      status: 'error',
      upstream: upstreamUrl,
      error: err.message,
    }, { status: 500 });
  }
}