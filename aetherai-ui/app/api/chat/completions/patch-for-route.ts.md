const encoder = new TextEncoder();
const decoder = new TextDecoder();
const parser = new StreamParser();

const stream = new ReadableStream({
  async start(controller) {
    const emit = (payload: object) => {
      controller.enqueue(encoder.encode(`data: ${JSON.stringify(payload)}\n\n`));
    };

    try {
      const contentType = upstreamResponse.headers.get('content-type') || '';

      // 🔹 Non-SSE upstream (single JSON completion)
      if (!contentType.includes('text/event-stream')) {
        const json = await upstreamResponse.json();

        // Be very forgiving about shape
        const choice = Array.isArray(json.choices) ? json.choices[0] : undefined;
        const fullText =
          choice?.message?.content ??
          choice?.text ??
          (typeof json.content === 'string' ? json.content : '') ??
          '';

        if (fullText && fullText.trim()) {
          const segments = parser.parse(fullText);

          for (const seg of segments) {
            if (!seg.content?.trim()) continue;

            if (seg.type === 'thinking') {
              emit({ type: 'thinking', content: seg.content });
            } else {
              emit({ type: 'content', content: seg.content });
            }
          }
        }

        // End of stream
        controller.enqueue(encoder.encode('data: [DONE]\n\n'));
        controller.close();
        return;
      }

      // 🔹 SSE upstream (current behavior)
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
          if (!line.startsWith('data: ') || line === 'data: [DONE]') continue;

          try {
            const json = JSON.parse(line.slice(6));
            const delta = json.choices?.[0]?.delta;
            if (!delta) continue;

            // === Tool calls (unchanged) ===
            if (delta.tool_calls) {
              const toolDelta = delta.tool_calls[0];
              const { complete, toolCall } = parser.accumulateToolCall(toolDelta);

              if (complete && toolCall) {
                emit({
                  type: 'tool_use',
                  tool: toolCall.name,
                  query: toolCall.arguments.query,
                  status: 'searching',
                });

                if (toolCall.name === 'web_search') {
                  try {
                    const searchResponse = await fetch(
                      `${process.env.SEARCH_API_URL || 'http://localhost:3000/api/search'}`,
                      {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                          query: toolCall.arguments.query,
                          num_results: toolCall.arguments.num_results || 5,
                        }),
                      }
                    );

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

            // === Content chunks ===
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

      // Flush any remaining buffered content
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
