import { NextRequest, NextResponse } from 'next/server';

// --- APRIEL 1.6 SYSTEM PROMPT (RESEARCHED & FIXED) ---
// 1. Mandatory: explicit instruction to use <think> and [BEGIN FINAL RESPONSE]
// 2. Mandatory: "AetherPro" persona integrated into the standard template
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

// Artifacts to clean for the *user facing* stream (we hide the raw markers)
const ARTIFACT_PATTERNS = [
  /\[BEGIN FINAL RESPONSE\]/gi,
  /<\|end\|>/gi,
  /<\|endoftext\|>/gi,
];

function cleanArtifacts(content: string): string {
  let cleaned = content;
  for (const pattern of ARTIFACT_PATTERNS) {
    cleaned = cleaned.replace(pattern, '');
  }
  return cleaned;
}

/**
 * StreamParser: Handles 1.6's specific <think> ... [BEGIN FINAL RESPONSE] flow
 */
class StreamParser {
  private buffer = '';
  private isThinking = false;
  private pendingToolCall: { name?: string; arguments: string } | null = null;

  parse(chunk: string): Array<{
    type: 'thinking' | 'content' | 'tool_call_start' | 'tool_call_complete';
    content?: string;
    toolCall?: { name: string; arguments: any };
  }> {
    this.buffer += chunk;
    const results: Array<any> = [];

    while (true) {
      if (!this.isThinking) {
        // 1. Detect Start of Thinking
        const thinkStart = this.buffer.indexOf('<think>');
        if (thinkStart !== -1) {
          const before = this.buffer.slice(0, thinkStart);
          if (before.trim()) results.push({ type: 'content', content: cleanArtifacts(before) });
          this.buffer = this.buffer.slice(thinkStart + 7);
          this.isThinking = true;
          continue;
        }

        // 2. Detect Final Response Marker (The prompt mandates this now)
        const marker = "[BEGIN FINAL RESPONSE]";
        const markerIdx = this.buffer.indexOf(marker);
        if (markerIdx !== -1) {
            // Just consume the marker and continue treating rest as content
            this.buffer = this.buffer.slice(markerIdx + marker.length);
            continue;
        }

        // 3. Normal Content
        if (this.buffer.length > 50) { // Keep small buffer for safety
             const output = this.buffer.slice(0, -20);
             results.push({ type: 'content', content: cleanArtifacts(output) });
             this.buffer = this.buffer.slice(-20);
        }
        break;

      } else {
        // 4. Detect End of Thinking
        const thinkEnd = this.buffer.indexOf('</think>');
        if (thinkEnd !== -1) {
          const thinking = this.buffer.slice(0, thinkEnd);
          if (thinking.trim()) results.push({ type: 'thinking', content: thinking });
          this.buffer = this.buffer.slice(thinkEnd + 8);
          this.isThinking = false;
          continue;
        }
        
        // Emit thinking chunk
        if (this.buffer.length > 50) {
            const thought = this.buffer.slice(0, -20);
            results.push({ type: 'thinking', content: thought });
            this.buffer = this.buffer.slice(-20);
        }
        break;
      }
    }
    return results;
  }

  // ... (Tool accumulation logic remains same as your working version) ...
  accumulateToolCall(delta: any): { complete: boolean; toolCall?: { name: string; arguments: any } } {
    if (!this.pendingToolCall) this.pendingToolCall = { arguments: '' };
    if (delta.function?.name) this.pendingToolCall.name = delta.function.name;
    if (delta.function?.arguments) this.pendingToolCall.arguments += delta.function.arguments;

    if (this.pendingToolCall.name && this.pendingToolCall.arguments) {
      try {
        const args = JSON.parse(this.pendingToolCall.arguments);
        const result = { name: this.pendingToolCall.name, arguments: args };
        this.pendingToolCall = null;
        return { complete: true, toolCall: result };
      } catch { return { complete: false }; }
    }
    return { complete: false };
  }

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

    // Inject the FIXED system prompt
    const fullMessages = [
      { role: 'system', content: SYSTEM_PROMPT },
      ...messages
    ];

    const upstreamUrl = process.env.AETHER_UPSTREAM_URL || 'http://localhost:8001/v1/chat/completions';

    const upstreamResponse = await fetch(upstreamUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${process.env.AETHER_API_KEY || 'sk-aether-sovereign-master-key-2026'}`,
      },
      body: JSON.stringify({
        model: model || 'apriel',
        messages: fullMessages,
        // --- 1.6 OPTIMIZED PARAMETERS ---
        temperature: 0.6,        // Lower temp for stability
        repetition_penalty: 1.0, // DISABLED (1.0) to prevent thought loops
        max_tokens: 8192,
        top_p: 0.95,             // Slightly higher for better reasoning flow
        stream: true,
        tools: TOOLS,
        tool_choice: 'auto',
      }),
      signal: AbortSignal.timeout(600000), 
    });

    if (!upstreamResponse.ok) {
      const errText = await upstreamResponse.text();
      console.error('Upstream Error:', errText);
      throw new Error(`Upstream Error: ${upstreamResponse.status} - ${errText}`);
    }

    const encoder = new TextEncoder();
    const decoder = new TextDecoder();
    const parser = new StreamParser();

    const stream = new ReadableStream({
      async start(controller) {
        const emit = (payload: object) => {
          controller.enqueue(encoder.encode(`data: ${JSON.stringify(payload)}\n\n`));
        };

        try {
          const reader = upstreamResponse.body?.getReader();
          if (!reader) { controller.close(); return; }

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
                
                if (delta) {
                  // 1. Tool Calls
                  if (delta.tool_calls) {
                    const toolDelta = delta.tool_calls[0];
                    const { complete, toolCall } = parser.accumulateToolCall(toolDelta);
                    if (complete && toolCall) {
                      emit({ type: 'tool_use', tool: toolCall.name, query: toolCall.arguments.query, status: 'searching' });
                      // ... (Your existing tool execution logic goes here) ...
                      if (toolCall.name === 'web_search') {
                         // Re-insert your fetch logic here from your previous file
                         // I am abbreviating it to save space, but DO NOT delete it.
                         try {
                            const searchResponse = await fetch(`${process.env.SEARCH_API_URL || 'http://localhost:3000/api/search'}`, {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ query: toolCall.arguments.query, num_results: 5 })
                            });
                            if (searchResponse.ok) {
                                const data = await searchResponse.json();
                                emit({ type: 'tool_result', tool: 'web_search', query: toolCall.arguments.query, results: data.results || [], status: 'complete' });
                            } else {
                                emit({ type: 'tool_error', tool: 'web_search', error: 'Search failed' });
                            }
                         } catch (e) { emit({ type: 'tool_error', tool: 'web_search', error: String(e) }); }
                      }
                    }
                    continue; 
                  }

                  // 2. Text Content (Thinking + Response)
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
                  emit(json);
                }
              } catch (e) {}
            }
          }
          
          const remaining = parser.flush();
          for (const seg of remaining) {
             if (seg.content?.trim()) emit({ type: seg.type, content: seg.content });
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
      headers: { 'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache', 'Connection': 'keep-alive' },
    });

  } catch (error: any) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}