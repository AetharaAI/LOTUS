'use client';

import { useState } from 'react';
import { useChatStore } from '@/lib/stores/chatStore';
import { MessageList } from './MessageList';
import { InputBar } from './InputBar';
import { Sidebar } from './Sidebar';
import { streamChat } from '@/lib/streaming';

export default function ChatInterface() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
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
  } = useChatStore();

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
    });

    // Track response content as it streams
    let thinkingContent = '';
    let responseContent = '';

    try {
      const contextMessages = useChatStore.getState().getContext();
      await streamChat(
        {
          messages: contextMessages,
          model: currentModel === 'auto' ? 'apriel-1.5-15b-thinker' : currentModel,
          temperature: 0.7,
          enable_tools: true,
        },
        {
          // === Thinking Callbacks ===
          onThinkingStart: () => {
            // Optional: Show thinking indicator
          },

          onThinking: (chunk: string) => {
            thinkingContent += chunk;
            updateLastMessage({
              thinking: thinkingContent,
            });
          },

          onThinkingEnd: (fullThinking: string) => {
            // Use the complete thinking if provided
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
            // Optional: Indicate final response starting
          },

          onFinalResponse: (response: string) => {
            // Use the complete final response if provided
            if (response) {
              responseContent = response;
              updateLastMessage({
                content: responseContent,
              });
            }
          },

          // === Tool Callbacks ===
          onToolUse: (data) => {
            setCurrentToolUse({
              tool: data.tool,
              query: data.query,
              results: data.results,
              isSearching: data.status === 'searching',
            });
          },

          onToolCallsDetected: (calls) => {
            // Multiple tools detected - show first one
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

            // Auto-clear tool display after a delay
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
            // If final response provided, use it
            if (finalResponse && !responseContent) {
              updateLastMessage({
                content: finalResponse,
              });
            }
            setIsStreaming(false);
            setCurrentToolUse(null);
          },

          onError: (error: string) => {
            console.error('Stream error:', error);
            updateLastMessage({
              content: responseContent || `Error: ${error}`,
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
      {/* Sidebar - Desktop always visible, Mobile toggleable */}
      <div
        className={`
          fixed md:relative z-50 md:z-auto
          w-80 h-full
          transform transition-transform duration-300 ease-in-out
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}
        `}
      >
        <Sidebar onClose={() => setSidebarOpen(false)} />
      </div>

      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Main chat area */}
      <div className="flex-1 flex flex-col">
        {/* Header with mobile menu toggle */}
        <header className="h-16 border-b border-aether-indigo-light flex items-center px-4 md:px-6 bg-aether-bg-card">
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="md:hidden mr-4 text-aether-text hover:text-aether-purple-light transition-colors"
          >
            <svg
              width="24"
              height="24"
              viewBox="0 0 24 24"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                d="M3 12H21M3 6H21M3 18H21"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </button>

          <div className="flex-1">
            <h1 className="text-lg font-semibold bg-gradient-to-r from-aether-purple-light to-aether-indigo-light bg-clip-text text-transparent">
              AetherAI
            </h1>
            <p className="text-xs text-aether-text-muted">
              Powered by Apriel • Sovereign US Infrastructure
            </p>
          </div>

          {/* Model badge */}
          <div className="hidden md:flex items-center gap-2 px-3 py-1.5 bg-aether-bg-dark rounded-full border border-aether-indigo-light">
            <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
            <span className="text-xs font-medium">
              {currentModel === 'auto' ? 'Apriel (Auto)' : currentModel.toUpperCase()}
            </span>
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