/**
 * Sidebar Component
 *
 * Conversation history and model selector.
 */

'use client';

import { useChatStore } from '@/lib/stores/chatStore';
import { Button } from '../shared/Button';
import { Logo } from '../shared/Logo';

interface SidebarProps {
  className?: string;
  onClose?: () => void;
}

export function Sidebar({ className = '', onClose }: SidebarProps) {
  const {
    conversations,
    currentConversationId,
    currentModel,
    setCurrentModel,
    loadConversation,
    createNewConversation,
    deleteConversation,
  } = useChatStore();

  const handleNewChat = () => {
    createNewConversation();
    onClose?.();
  };

  const handleLoadConversation = (id: string) => {
    loadConversation(id);
    onClose?.();
  };

  return (
    <div
      className={`flex flex-col h-full bg-aether-bg-card border-r border-aether-indigo-light ${className}`}
    >
      {/* Header */}
      <div className="p-4 border-b border-aether-indigo-light">
        <div className="flex items-center justify-between mb-4">
          <Logo size="sm" />
          {/* Mobile close button */}
          {onClose && (
            <button
              onClick={onClose}
              className="md:hidden text-aether-text-muted hover:text-aether-text transition-colors"
            >
              <svg
                width="24"
                height="24"
                viewBox="0 0 24 24"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
              >
                <path
                  d="M18 6L6 18M6 6L18 18"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </button>
          )}
        </div>

        {/* New Chat Button */}
        <Button onClick={handleNewChat} variant="primary" size="md" className="w-full">
          <span className="flex items-center justify-center gap-2">
            <svg
              width="20"
              height="20"
              viewBox="0 0 20 20"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                d="M10 4V16M4 10H16"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
            New Chat
          </span>
        </Button>
      </div>

      {/* Model Selector */}
      <div className="p-4 border-b border-aether-indigo-light">
        <label className="block text-xs text-aether-text-muted mb-2 font-semibold">
          Model Selection
        </label>
        <select
          value={currentModel}
          onChange={(e) => setCurrentModel(e.target.value as any)}
          className="w-full bg-aether-bg-dark border border-aether-indigo-light rounded-lg px-3 py-2 text-aether-text text-sm focus:outline-none focus:ring-2 focus:ring-aether-purple-light transition-all"
        >
          <option value="auto">🤖 Auto-Select (Smart Routing)</option>
          <option value="apriel">🏠 Apriel (Self-Hosted, Free)</option>
          <option value="grok">🧠 Grok-2 (Advanced Reasoning)</option>
          <option value="claude">👁️ Claude (Vision + Analysis)</option>
        </select>
        <p className="mt-2 text-xs text-aether-text-muted">
          {currentModel === 'auto' && 'Routes to best model automatically'}
          {currentModel === 'apriel' && 'Fast, reliable, US-hosted'}
          {currentModel === 'grok' && 'Complex reasoning tasks'}
          {currentModel === 'claude' && 'Image analysis & deep insights'}
        </p>
      </div>

      {/* Conversations List */}
      <div className="flex-1 overflow-y-auto p-4">
        <h3 className="text-xs text-aether-text-muted font-semibold mb-3">
          Recent Conversations
        </h3>

        {conversations.length === 0 ? (
          <div className="text-sm text-aether-text-muted text-center py-8">
            No conversations yet.
            <br />
            Start chatting to see history here.
          </div>
        ) : (
          <div className="space-y-2">
            {conversations.map((conversation) => {
              const isActive = conversation.id === currentConversationId;

              return (
                <div
                  key={conversation.id}
                  className={`group relative rounded-lg p-3 cursor-pointer transition-all ${
                    isActive
                      ? 'bg-gradient-to-r from-aether-purple-dark to-aether-purple-light text-white'
                      : 'bg-aether-bg-dark hover:bg-aether-bg-hover text-aether-text'
                  }`}
                  onClick={() => handleLoadConversation(conversation.id)}
                >
                  {/* Title */}
                  <h4 className="font-semibold text-sm truncate mb-1">
                    {conversation.title}
                  </h4>

                  {/* Metadata */}
                  <div className="flex items-center gap-2 text-xs opacity-80">
                    <span>
                      {conversation.messages.length}{' '}
                      {conversation.messages.length === 1 ? 'message' : 'messages'}
                    </span>
                    <span>•</span>
                    <span>
                      {new Date(conversation.updatedAt).toLocaleDateString()}
                    </span>
                  </div>

                  {/* Delete button */}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      if (
                        confirm(
                          `Delete "${conversation.title}"? This cannot be undone.`
                        )
                      ) {
                        deleteConversation(conversation.id);
                      }
                    }}
                    className={`absolute top-2 right-2 p-1 rounded opacity-0 group-hover:opacity-100 transition-opacity ${
                      isActive
                        ? 'hover:bg-white/20'
                        : 'hover:bg-aether-indigo-light'
                    }`}
                  >
                    <svg
                      width="16"
                      height="16"
                      viewBox="0 0 16 16"
                      fill="none"
                      xmlns="http://www.w3.org/2000/svg"
                    >
                      <path
                        d="M2 4H14M5.5 4V2.5C5.5 2.22386 5.72386 2 6 2H10C10.2761 2 10.5 2.22386 10.5 2.5V4M12.5 4V13.5C12.5 13.7761 12.2761 14 12 14H4C3.72386 14 3.5 13.7761 3.5 13.5V4"
                        stroke="currentColor"
                        strokeWidth="1.5"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </svg>
                  </button>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-aether-indigo-light text-xs text-aether-text-muted">
        <p className="mb-1">
          <span className="text-aether-purple-light font-semibold">AetherAI</span>
        </p>
        <p>The American Standard for Sovereign AI</p>
        <p className="mt-2 text-[10px]">
          Your data stays on US soil. 🇺🇸
        </p>
      </div>
    </div>
  );
}
