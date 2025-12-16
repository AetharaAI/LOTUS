'use client';

import { useState } from 'react';
import { useChatStore } from '@/lib/stores/chatstore';
import { streamChat } from '@/lib/streaming';

export function ChatInterface() {
  const { 
    messages, 
    addMessage, 
    updateLastMessage, 
    setIsStreaming,
    isStreaming,
    currentModel,
    getContext 
  } = useChatStore();

  const [input, setInput] = useState('');

  const handleSend = async () => {
    if (!input.trim() || isStreaming) return;

    const userMessage = input.trim();
    setInput('');

    // Add user message
    addMessage({ 
      role: 'user', 
      content: userMessage 
    });

    // Add empty assistant message to update
    addMessage({ 
      role: 'assistant', 
      content: '',
      model: currentModel 
    });

    setIsStreaming(true);

    try {
      // Get conversation context
      const context = getContext();
      
      // Stream the response
      await streamChat(
        [...context, { role: 'user', content: userMessage }],
        currentModel,
        {
          onContent: (content) => {
            // Append content to last message
            updateLastMessage({ 
              content: (messages[messages.length - 1]?.content || '') + content 
            });
          },
          
          onToolCall: (toolCall) => {
            console.log('Tool call:', toolCall);
            // Handle tool calls if needed
          },
          
          onFinish: (reason) => {
            console.log('Stream finished:', reason);
            setIsStreaming(false);
          },
          
          onError: (error) => {
            console.error('Stream error:', error);
            updateLastMessage({ 
              content: `Error: ${error}` 
            });
            setIsStreaming(false);
          }
        }
      );
    } catch (error) {
      console.error('Chat error:', error);
      updateLastMessage({ 
        content: `Error: ${String(error)}` 
      });
      setIsStreaming(false);
    }
  };

  return (
    <div className="flex flex-col h-screen">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${
              message.role === 'user' ? 'justify-end' : 'justify-start'
            }`}
          >
            <div
              className={`max-w-[80%] rounded-lg p-4 ${
                message.role === 'user'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-900'
              }`}
            >
              <div className="prose prose-sm">
                {message.content}
              </div>
              {message.thinking && (
                <details className="mt-2 text-xs opacity-70">
                  <summary>View reasoning</summary>
                  <pre className="mt-1 whitespace-pre-wrap">
                    {message.thinking}
                  </pre>
                </details>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Input */}
      <div className="border-t p-4">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSend()}
            disabled={isStreaming}
            placeholder="Message Apriel..."
            className="flex-1 px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            onClick={handleSend}
            disabled={isStreaming || !input.trim()}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isStreaming ? 'Sending...' : 'Send'}
          </button>
        </div>
      </div>
    </div>
  );
}