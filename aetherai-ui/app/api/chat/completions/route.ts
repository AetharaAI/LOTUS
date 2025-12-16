import { NextRequest, NextResponse } from 'next/server';

// --- SYSTEM PROMPT (keeps Apriel behavior, works for 1.5 & 1.6) ---
const SYSTEM_PROMPT = `You are Apriel, Sovereign AI of AetherPro Technologies.

ROLE & PERSONA:
- You are a Senior Technical Advisor and AI Architect for sovereign infrastructure.
- Tone: Professional, direct, high-signal. No fluff.
- Voice: Modern American Engineering (e.g., "Let's deploy this," not "We shall henceforth").

CRITICAL OUTPUT RULES (DO NOT VIOLATE):
1. START with your reasoning process enclosed in <think>...</think> tags.
2. AFTER reasoning, output the marker "[BEGIN FINAL RESPONSE]".
3. PROVIDE your actual response to the user AFTER that marker.

STRUCTURE:
- Direct Answer: 1-2 sentences immediately after the final response marker.
- Details: Use bullet points for clarity.
- Tool Usage: If you need to search, output the tool call clearly.

YOUR GOAL:
Solve the user's problem with sovereign, self-hosted solutions. Privacy is the product.`;

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
            description: 'The search query. Be specific and concise.'
          },
          num_results: {
            type: 'integer',
            description: 'Number of results to return (1-10). Default is 5.',
            default: 5
          }
        },
        required: ['query']
      }
    }
  }
];

// Markers we strip out before sending to the frontend
const ARTIFACT_PATTERNS = [
  /\[BEGIN FINAL RESPONSE\]/gi,
  /\[END FINAL RESPONSE\]/gi,     // 1.5-style
  /<\|end\|>/gi,                  // 1.6-style
  /<\|endoftext\|>/gi
];

function cleanArtifacts(content: string): string {
  let cleaned = content;
  for (const pattern of ARTIFACT_PATTERNS) {
    cleaned = cleaned.replace(pattern, '');
  }
  return cleaned;
}

/**
 * VERY SIMPLE stream parser:
 * - Splits <think>...</think> blocks into "thinking" events
 * - Everything else is "content"
 * - No buffering games, so we NEVER swallow tokens.
 * Works for both 1.5 and 1.6; frontend just gets chunks.
 */
class StreamParser {
  private pendingToolCall: { name?: string; arguments: string } | null = null;

  parse(
    chunk: string
  ): Array<{ type: 'thinking' | 'content'; content: string }> {
    const results: Array<{ type: 'thinking' | 'content'; content: string }> =
      [];

    let remaining = chunk;

    while (true) {
      const start = remaining.indexOf('<think>');
      const end = remaining.indexOf('</think>');

      if (start !== -1 && end !== -1 && end > start) {
        // Text before <think> is normal content
        const before = remaining.slice(0, start);
        if (before.trim()) {
          results.push({
            type: 'content',
            content: cleanArtifacts(before)
          });
        }

        // Actual thinking block
        const thought = remaining.slice(start + 7, end);
        if (thought.trim()) {
          results.push({
            type: 'thinking',
            content: thought
          });
        }

        // Continue parsing after </think>
        remaining = remaining.slice(end + 8);
        continue;
      }

      // No complete <think> block left, treat the rest as content
      if (remaining.trim()) {
        results.push({
          type: 'content',
          content: cleanArtifacts(remaining)
        });
      }
      break;
    }

    return results;
  }

  // Tool call accumulator stays the same
  accumulateToolCall(delta: any): {
    complete: boolean;
    toolCall?: { name: string; arguments: any };
  } {
    if (!this.pendingToolCall) this.pendingToolCall = { arguments: '' };
    if (delta.function?.name) this.pendingToolCall.name = delta.function.name;
    if (delta.function?.arguments)
      this.pendingToolCall.arguments += delta.function.arguments;

    if (this.pendingToolCall.name && this.pendingToolCall.arguments) {
      try {
        const args = JSON.parse(this.pendingToolCall.arguments);
        const result = {
          name: this.pendingToolCall.name,
          arguments: args
        };
        this.pendingToolCall = null;
        return { complete: true, toolCall: result };
      } catch {
        return { complete: false };
      }
    }
    return { complete: false };
  }

  // Nothing buffered long-term, so flush is a no-op
  flush(): Array<{ type: 'thinking' | 'content'; content: string }> {
    return [];
  }
}

export async function POST(req: NextRequest) {
  try {
    const { messages, model } = await req.json();

    // Inject system prompt in front of user messages
    const fullMessages = [
      { role: 'system', content: SYSTEM_PROMPT },
      ...messages
    ];

    // IMPORTANT: keep model name as "apriel" (LiteLLM mapping)
    const upstreamUrl =
      process.env.AETHER_UPSTREAM_URL ||
      'http://localhost:8001/v1/chat/completions';

    const upstreamResponse = await fetch(upstreamUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${
          process.env.AETHER_API_KEY ||
          'sk-aether-sovereign-master-key-2026'
        }`
      },
      body: JSON.stringify({
        model: model || 'apriel',
        messages: fullMessages,
        temperature: 0.6,
        repetition_penalty: 1.0,
        max_tokens: 8192,
        top_p: 0.95,
        stream: true,
        tools: TOOLS,
        tool_choice: 'auto'
      }),
      signal: AbortSignal.timeout(600000)
    });

    if (!upstreamResponse.ok) {
      const errText = await upstreamResponse.text();
      console.error('Upstream Error:', errText);
      throw new Error(
        `Upstream Error: ${upstreamResponse.status} - ${errText}`
      );
    }

    const encoder = new TextEncoder();
    const decoder = new TextDecoder();
    const parser = new StreamParser();

    const stream = new ReadableStream({
      async start(controller) {
        const emit = (payload: object) => {
          controller.enqueue(
            encoder.encode(`data: ${JSON.stringify(payload)}\n\n`)
          );
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
                  // --- Tool calls ---
                  if (delta.tool_calls) {
                    const toolDelta = delta.tool_calls[0];
                    const { complete, toolCall } =
                      parser.accumulateToolCall(toolDelta);

                    if (complete && toolCall) {
                      emit({
                        type: 'tool_use',
                        tool: toolCall.name,
                        query: toolCall.arguments.query,
                        status: 'searching'
                      });

                      if (toolCall.name === 'web_search') {
                        try {
                          const searchResponse = await fetch(
                            process.env.SEARCH_API_URL ||
                              'http://localhost:3000/api/search',
                            {
                              method: 'POST',
                              headers: { 'Content-Type': 'application/json' },
                              body: JSON.stringify({
                                query: toolCall.arguments.query,
                                num_results: 5
                              })
                            }
                          );

                          if (searchResponse.ok) {
                            const data = await searchResponse.json();
                            emit({
                              type: 'tool_result',
                              tool: 'web_search',
                              query: toolCall.arguments.query,
                              results: data.results || [],
                              status: 'complete'
                            });
                          } else {
                            emit({
                              type: 'tool_error',
                              tool: 'web_search',
                              error: 'Search failed'
                            });
                          }
                        } catch (e) {
                          emit({
                            type: 'tool_error',
                            tool: 'web_search',
                            error: String(e)
                          });
                        }
                      }
                    }

                    continue;
                  }

                  // --- Normal text content (thinking + final) ---
                  const content = delta.content;
                  if (content) {
                    const segments = parser.parse(content);
                    for (const seg of segments) {
                      if (seg.content?.trim() || seg.type === 'thinking') {
                        emit({ type: seg.type, content: seg.content });
                      }
                    }
                  }
                } else {
                  // pass through any non-delta events (e.g. metadata)
                  emit(json);
                }
              } catch {
                // ignore malformed JSON lines
              }
            }
          }

          const remaining = parser.flush();
          for (const seg of remaining) {
            if (seg.content?.trim()) {
              emit({ type: seg.type, content: seg.content });
            }
          }

          controller.enqueue(encoder.encode('data: [DONE]\n\n'));
          controller.close();
        } catch (error) {
          console.error('Stream error:', error);
          controller.close();
        }
      }
    });

    return new NextResponse(stream, {
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        Connection: 'keep-alive'
      }
    });
  } catch (error: any) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
