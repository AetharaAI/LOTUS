import { create } from 'zustand';

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  thinking?: string;
  model?: string;
  timestamp: Date;
}

export interface Conversation {
  id: string;
  title: string;
  messages: Message[];
  model: string;
  createdAt: Date;
  updatedAt: Date;
}

interface ChatState {
  // Current conversation
  messages: Message[];
  currentConversationId: string | null;
  isStreaming: boolean;

  // Model selection
  currentModel: 'auto' | 'apriel' | 'grok' | 'claude';

  // Conversations list
  conversations: Conversation[];

  // Actions
  addMessage: (message: Omit<Message, 'id' | 'timestamp'>) => void;
  updateLastMessage: (updates: Partial<Message>) => void;
  clearMessages: () => void;
  setIsStreaming: (streaming: boolean) => void;
  setCurrentModel: (model: 'auto' | 'apriel' | 'grok' | 'claude') => void;
  loadConversation: (conversationId: string) => void;
  createNewConversation: () => void;
  deleteConversation: (conversationId: string) => void;
}

export const useChatStore = create<ChatState>((set, get) => ({
  // Initial state
  messages: [],
  currentConversationId: null,
  isStreaming: false,
  currentModel: 'auto',
  conversations: [],

  // Actions
  addMessage: (message) => {
    const newMessage: Message = {
      ...message,
      id: crypto.randomUUID(),
      timestamp: new Date(),
    };

    set((state) => ({
      messages: [...state.messages, newMessage],
    }));
  },

  updateLastMessage: (updates) => {
    set((state) => {
      const messages = [...state.messages];
      const lastIndex = messages.length - 1;

      if (lastIndex >= 0) {
        messages[lastIndex] = {
          ...messages[lastIndex],
          ...updates,
        };
      }

      return { messages };
    });
  },

  clearMessages: () => {
    set({ messages: [], currentConversationId: null });
  },

  setIsStreaming: (streaming) => {
    set({ isStreaming: streaming });
  },

  setCurrentModel: (model) => {
    set({ currentModel: model });
  },

  loadConversation: (conversationId) => {
    // TODO: Load conversation from API/storage
    const conversation = get().conversations.find(
      (c) => c.id === conversationId
    );

    if (conversation) {
      set({
        messages: conversation.messages,
        currentConversationId: conversationId,
        currentModel: conversation.model as any,
      });
    }
  },

  createNewConversation: () => {
    set({
      messages: [],
      currentConversationId: null,
      currentModel: 'auto',
    });
  },

  deleteConversation: (conversationId) => {
    set((state) => ({
      conversations: state.conversations.filter(
        (c) => c.id !== conversationId
      ),
    }));

    // If deleting current conversation, clear messages
    if (get().currentConversationId === conversationId) {
      get().clearMessages();
    }
  },
}));
