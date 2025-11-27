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
VOICE: Direct, modern American English. Never use archaic words like "henceforth", "thusly", "whilst", "hereby". Write like a senior engineer on Slack, not a Victorian professor.
- You're a senior engineer at AetherPro Technologies, specializing in sovereign AI infrastructure
- Your expertise includes distributed systems, quantum-resistant cryptography, and AI safety
- You're known for your ability to explain complex technical concepts clearly
- You have a strong background in both software engineering and AI research
TOOL USAGE:
- You have access to web_search for current information
- Use ONLY when query requires recent data or facts beyond your training
- Always cite sources when using search results

RESPONSE FORMAT:
- Put all reasoning inside <think>...</think> tags
- After </think>, provide ONLY your final answer
- Do NOT use [BEGIN FINAL RESPONSE] or similar markers
- Do NOT output LaTeX or document markers

RESPONSE STRUCTURE:
1. Direct answer (1-2 sentences)
2. Key supporting points (2-3 bullets if needed)
3. Offer to elaborate: "Need more detail on anything?"`;

const TOOLS = [
  {
    type: 'function',
    function: {
      name: 'web_search',
      description: 'Search the web for current information, recent news, or facts not in training data.',
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

// Artifacts to strip from model output
const ARTIFACT_PATTERNS = [
  /\[BEGIN FINAL RESPONSE\]/gi,
  /\[END FINAL RESPONSE\]/gi,
  /<\|end\|>/gi,
  /<\|endoftext\|>/gi,
  /\\end\{document\}/gi,
  /\\begin\{document\}/gi,
  /\\boxed\{[^}]*\}/gi,
  /Here are my reasoning steps:/gi,
  /\(Quick take\):/gi,
];

function cleanArtifacts(content: string): string {
  let cleaned = content;
  for (const pattern of ARTIFACT_PATTERNS) {
    cleaned = cleaned.replace(pattern, '');
  }
  return cleaned;
}

/**
 * StreamParser handles partial tag detection across chunk boundaries
 */
class StreamParser {
  private buffer = '';
  private isThinking = false;
  private pendingToolCall: { name?: string; arguments: string } | null = null;

  /**
   * Process incoming chunk and return parsed segments
   */
  parse(chunk: string): Array<{
    type: 'thinking' | 'content' | 'tool_call_start' | 'tool_call_complete';
    content?: string;
    toolCall?: { name: string; arguments: any };
  }> {
    this.buffer += chunk;
    const results: Array<any> = [];

    // Process complete tags in buffer
    while (true) {
      if (!this.isThinking) {
        // Look for <think> tag
        const thinkStart = this.buffer.indexOf('<think>');
        if (thinkStart !== -1) {
          // Emit any content before the tag
          const before = this.buffer.slice(0, thinkStart);
          if (before.trim()) {
            results.push({ type: 'content', content: cleanArtifacts(before) });
          }
          this.buffer = this.buffer.slice(thinkStart + 7);
          this.isThinking = true;
          continue;
        }

        // Check if buffer might contain partial <think> tag at end
        const partialThink = this.findPartialTag(this.buffer, '<think>');
        if (partialThink > 0) {
          // Emit content before potential partial tag
          const safe = this.buffer.slice(0, partialThink);
          if (safe.trim()) {
            results.push({ type: 'content', content: cleanArtifacts(safe) });
          }
          this.buffer = this.buffer.slice(partialThink);
          break;
        }

        // No tags found, emit all as content
        if (this.buffer.trim()) {
          results.push({ type: 'content', content: cleanArtifacts(this.buffer) });
        }
        this.buffer = '';
        break;
      } else {
        // Currently in thinking mode, look for </think>
        const thinkEnd = this.buffer.indexOf('</think>');
        if (thinkEnd !== -1) {
          // Emit thinking content
          const thinking = this.buffer.slice(0, thinkEnd);
          if (thinking.trim()) {
            results.push({ type: 'thinking', content: cleanArtifacts(thinking) });
          }
          this.buffer = this.buffer.slice(thinkEnd + 8);
          this.isThinking = false;
          continue;
        }

        // Check for partial </think> tag
        const partialEnd = this.findPartialTag(this.buffer, '</think>');
        if (partialEnd > 0) {
          const safe = this.buffer.slice(0, partialEnd);
          if (safe.trim()) {
            results.push({ type: 'thinking', content: cleanArtifacts(safe) });
          }
          this.buffer = this.buffer.slice(partialEnd);
          break;
        }

        // No closing tag yet, emit all as thinking
        if (this.buffer.trim()) {
          results.push({ type: 'thinking', content: cleanArtifacts(this.buffer) });
        }
        this.buffer = '';
        break;
      }
    }

    return results;
  }

  /**
   * Find position where a partial tag might start at end of string
   */
  private findPartialTag(str: string, tag: string): number {
    for (let i = 1; i < tag.length; i++) {
      const partial = tag.slice(0, i);
      if (str.endsWith(partial)) {
        return str.length - i;
      }
    }
    return -1;
  }

  /**
   * Accumulate tool call arguments (they stream in fragments)
   */
  accumulateToolCall(delta: any): { complete: boolean; toolCall?: { name: string; arguments: any } } {
    if (!this.pendingToolCall) {
      this.pendingToolCall = { arguments: '' };
    }

    if (delta.function?.name) {
      this.pendingToolCall.name = delta.function.name;
    }

    if (delta.function?.arguments) {
      this.pendingToolCall.arguments += delta.function.arguments;
    }

    // Try to parse accumulated arguments
    if (this.pendingToolCall.name && this.pendingToolCall.arguments) {
      try {
        const args = JSON.parse(this.pendingToolCall.arguments);
        const result = {
          name: this.pendingToolCall.name,
          arguments: args,
        };
        this.pendingToolCall = null;
        return { complete: true, toolCall: result };
      } catch {
        // JSON not complete yet
        return { complete: false };
      }
    }

    return { complete: false };
  }

  /**
   * Flush any remaining buffer content
   */
  flush(): Array<{ type: 'thinking' | 'content'; content: string }> {
    const results: Array<any> = [];
    if (this.buffer.trim()) {
      const type = this.isThinking ? 'thinking' : 'content';
      results.push({ type, content: cleanArtifacts(this.buffer) });
    }
    this.buffer = '';
    return results;
  }
}

export async function POST(req: NextRequest) {
  try {
    const { messages, model } = await req.json();

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
        temperature: 0.85,
        repetition_penalty: 1.2,
        max_tokens: 2048,
        top_p: 0.9,
        frequency_penalty: 0.0,
        presence_penalty: 0.1,
        stream: true,
        tools: TOOLS,
        tool_choice: 'auto',
      }),
    });

    if (!upstreamResponse.ok) {
      const errText = await upstreamResponse.text();
      console.error('Upstream Error:', errText);
      throw new Error(`Upstream Error: ${upstreamResponse.status}`);
    }

    const encoder = new TextEncoder();
    const decoder = new TextDecoder();
    const parser = new StreamParser();

    const stream = new ReadableStream({
      async start(controller) {
        const reader = upstreamResponse.body?.getReader();
        if (!reader) return controller.close();

        const emit = (payload: object) => {
          controller.enqueue(encoder.encode(`data: ${JSON.stringify(payload)}\n\n`));
        };

        try {
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value, { stream: true });
            const lines = chunk.split('\n');

            for (const line of lines) {
              if (!line.startsWith('data: ') || line === 'data: [DONE]') continue;

              try {
                const json = JSON.parse(line.slice(6));
                const delta = json.choices?.[0]?.delta;
                if (!delta) continue;

                // Handle tool calls with accumulation
                if (delta.tool_calls) {
                  const toolDelta = delta.tool_calls[0];
                  const { complete, toolCall } = parser.accumulateToolCall(toolDelta);

                  if (complete && toolCall) {
                    // Emit tool start
                    emit({
                      type: 'tool_use',
                      tool: toolCall.name,
                      query: toolCall.arguments.query,
                      status: 'searching',
                    });

                    // Execute search
                    if (toolCall.name === 'web_search') {
                      try {
                        const searchResponse = await fetch(`${process.env.SEARCH_API_URL || 'http://localhost:3000/api/search'}`, {
                          method: 'POST',
                          headers: { 'Content-Type': 'application/json' },
                          body: JSON.stringify({
                            query: toolCall.arguments.query,
                            num_results: toolCall.arguments.num_results || 5,
                          }),
                        });

                        if (searchResponse.ok) {
                          const searchData = await searchResponse.json();
                          emit({
                            type: 'tool_result',
                            tool: 'web_search',
                            query: toolCall.arguments.query,
                            results: searchData.results || [],
                            status: 'complete',
                          });
                        } else {
                          emit({ type: 'tool_error', tool: 'web_search', error: 'Search failed' });
                        }
                      } catch (e) {
                        emit({ type: 'tool_error', tool: 'web_search', error: String(e) });
                      }
                    }
                  }
                  continue;
                }

                // Handle content with robust parsing
                const content = delta.content;
                if (!content) continue;

                const segments = parser.parse(content);
                for (const seg of segments) {
                  if (seg.content?.trim()) {
                    emit({ type: seg.type, content: seg.content });
                  }
                }

              } catch {
                // Ignore malformed JSON chunks
              }
            }
          }

          // Flush remaining buffer
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
    console.error('Route error:', error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}