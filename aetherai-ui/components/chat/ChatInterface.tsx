'use client';

import { useState, useMemo } from 'react';
import { useChatStore } from '@/lib/stores/chatStore';
import { MessageList } from './MessageList';
import { InputBar } from './InputBar';
import { Sidebar } from './Sidebar';
import { streamChat } from '@/lib/streaming';

const MODEL_OPTIONS = [
  {
    id: 'qwen3-vl-local',
    label: 'Qwen3-VL 30B (L40S-90)',
    description: 'Primary AetherAI model – local, vision-capable.',
  },
  {
    id: 'qwen3-omni-remote',
    label: 'Qwen3-Omni 30B (BlackBox)',
    description: 'Remote node via BlackBoxAudio OpenAI endpoint.',
  },
  {
    id: 'devstral-24b',
    label: 'Devstral 24B (Code)',
    description: 'Engineer model for heavy coding sessions.',
  },
];

export default function ChatInterface() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [toolsEnabled, setToolsEnabled] = useState(true);
  const [currentToolUse, setCurrentToolUse] = useState<{
    tool: string;
    query: string;
    results?: any[];
    isSearching: boolean;
  } | null>(null);

  const {
    messages,
    isStreaming,
    currentModel,
    addMessage,
    updateLastMessage,
    setIsStreaming,
    setCurrentModel,
  } = useChatStore();

  const activeModelMeta = useMemo(
    () => MODEL_OPTIONS.find((m) => m.id === currentModel) ?? MODEL_OPTIONS[0],
    [currentModel]
  );

  const handleSendMessage = async (content: string) => {
    if (!content.trim() || isStreaming) return;

    // Add user message
    addMessage({
      role: 'user',
      content: content.trim(),
    });

    // Prepare for assistant response
    setIsStreaming(true);

    // Create empty assistant message that we'll update
    addMessage({
      role: 'assistant',
      content: '',
      thinking: '',
      model: currentModel,
    });

    let thinkingContent = '';
    let responseContent = '';

    try {
      const contextMessages = useChatStore.getState().getContext();

      await streamChat(
        {
          messages: contextMessages,
          model: currentModel || 'qwen3-vl-local',
          temperature: 0.7,
          enable_tools: toolsEnabled,
        },
        {
          // === Thinking Callbacks (Qwen likely won’t use these, but harmless) ===
          onThinkingStart: () => {
            // could set a "thinking…" badge if you want
          },

          onThinking: (chunk: string) => {
            thinkingContent += chunk;
            updateLastMessage({
              thinking: thinkingContent,
            });
          },

          onThinkingEnd: (fullThinking: string) => {
            if (fullThinking) {
              thinkingContent = fullThinking;
              updateLastMessage({
                thinking: thinkingContent,
              });
            }
          },

          // === Content Callbacks ===
          onContent: (chunk: string) => {
            responseContent += chunk;
            updateLastMessage({
              content: responseContent,
            });
          },

          onFinalStart: () => {
            // hook if you want a “finalizing…” indicator
          },

          onFinalResponse: (response: string) => {
            if (response) {
              responseContent = response;
              updateLastMessage({
                content: responseContent,
              });
            }
          },

          // === Tool Callbacks (for web_search etc.) ===
          onToolUse: (data) => {
            setCurrentToolUse({
              tool: data.tool,
              query: data.query,
              results: data.results,
              isSearching: data.status === 'searching',
            });
          },

          onToolCallsDetected: (calls) => {
            if (calls.length > 0) {
              const firstCall = calls[0];
              setCurrentToolUse({
                tool: firstCall.name,
                query: firstCall.arguments?.query || '',
                isSearching: true,
              });
            }
          },

          onToolExecuting: (tool, args) => {
            setCurrentToolUse({
              tool,
              query: args.query || '',
              isSearching: true,
            });
          },

          onToolResult: (data) => {
            setCurrentToolUse({
              tool: data.tool,
              query: data.query,
              results: data.results,
              isSearching: false,
            });

            setTimeout(() => {
              setCurrentToolUse(null);
            }, 2000);
          },

          onToolError: (tool, error) => {
            console.error(`Tool ${tool} error:`, error);
            setCurrentToolUse(null);
          },

          // === Completion Callbacks ===
          onDone: (finalResponse?: string) => {
            if (finalResponse && !responseContent) {
              updateLastMessage({
                content: finalResponse,
              });
            }
            setIsStreaming(false);
            setCurrentToolUse(null);
          },

          onError: (error: any) => {
            console.error('Streaming error:', error);
            updateLastMessage({
              content:
                responseContent ||
                'AetherAI hit an upstream error. Try again in a moment.',
            });
            setIsStreaming(false);
            setCurrentToolUse(null);
          },
        }
      );
    } catch (error) {
      console.error('Chat error:', error);
      setIsStreaming(false);
      setCurrentToolUse(null);
    }
  };

  return (
    <div className="flex h-screen bg-aether-bg-dark text-aether-text">
      {/* Sidebar */}
      <Sidebar
        open={sidebarOpen}
        onToggle={() => setSidebarOpen(!sidebarOpen)}
      />

      {/* Main panel */}
      <div className="flex flex-col flex-1">
        {/* Top bar */}
        <header className="flex items-center justify-between px-4 py-3 border-b border-aether-border bg-aether-surface">
          <div className="flex items-center gap-2">
            <button
              className="md:hidden p-2 rounded-lg bg-aether-bg hover:bg-aether-bg-alt transition"
              onClick={() => setSidebarOpen(!sidebarOpen)}
            >
              ☰
            </button>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-lg font-semibold">AetherAI</span>
                <span className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded-full bg-emerald-900/40 text-emerald-300">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                  {activeModelMeta.label}
                </span>
              </div>
              <p className="text-xs text-aether-muted">
                Sovereign chat on your own GPU stack.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            {/* Model selector */}
            <div className="flex flex-col">
              <label className="text-[10px] uppercase tracking-wide text-aether-muted mb-1">
                Model
              </label>
              <select
                className="bg-aether-bg border border-aether-border text-sm rounded-lg px-2 py-1 focus:outline-none focus:ring-1 focus:ring-aether-accent"
                value={currentModel}
                onChange={(e) => setCurrentModel(e.target.value)}
                disabled={isStreaming}
              >
                {MODEL_OPTIONS.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Tools toggle */}
            <button
              type="button"
              onClick={() => setToolsEnabled((v) => !v)}
              className={`text-xs px-3 py-1 rounded-full border transition ${
                toolsEnabled
                  ? 'border-emerald-400 text-emerald-200 bg-emerald-900/30'
                  : 'border-aether-border text-aether-muted bg-aether-bg'
              }`}
            >
              {toolsEnabled ? 'Web Search: On' : 'Web Search: Off'}
            </button>
          </div>
        </header>

        {/* Messages */}
        <MessageList
          messages={messages}
          isStreaming={isStreaming}
          currentToolUse={currentToolUse}
        />

        {/* Input */}
        <InputBar onSend={handleSendMessage} disabled={isStreaming} />
      </div>
    </div>
  );
}
