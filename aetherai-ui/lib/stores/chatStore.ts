import { create } from 'zustand';
import { persist } from 'zustand/middleware';

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
  contextStartIndex?: number;
}

interface ChatState {
  // Current conversation
  messages: Message[];
  currentConversationId: string | null;
  isStreaming: boolean;

  // Model selection
  currentModel: string;
  


  // Conversations list
  conversations: Conversation[];

  // Actions
  addMessage: (message: Omit<Message, 'id' | 'timestamp'>) => void;
  updateLastMessage: (updates: Partial<Message>) => void;
  clearMessages: () => void;
  setIsStreaming: (streaming: boolean) => void;
  setCurrentModel: (model: string) => void;
  loadConversation: (conversationId: string) => void;
  createNewConversation: () => void;
  deleteConversation: (conversationId: string) => void;
  getContext: () => Message[];
  resetContext: () => void;
  getContextTokens: () => number;
}

export const useChatStore = create<ChatState>()(
  persist(
    (set, get) => ({
      // Initial state
      messages: [],
      currentConversationId: null,
      isStreaming: false,
      currentModel: 'qwen3-vl-local',
      conversations: [],

      // Actions
      addMessage: (message) => {
        const newMessage: Message = {
          ...message,
          id: crypto.randomUUID(),
          timestamp: new Date(),
        };
  
        set((state) => {
          const messages = [...state.messages, newMessage];
          const currentId = state.currentConversationId;
          if (currentId) {
            const convIndex = state.conversations.findIndex(c => c.id === currentId);
            if (convIndex !== -1) {
              const conv = state.conversations[convIndex];
              const updatedConv: Conversation = {
                ...conv,
                updatedAt: new Date(),
                messages,
              };
              // Auto-title if first assistant message
              if (conv.messages.length === 0 && message.role === 'assistant') {
                const firstUser = state.messages.find(m => m.role === 'user');
                if (firstUser) {
                  updatedConv.title = firstUser.content.slice(0, 50) + '...';
                }
              }
              const conversations = [...state.conversations];
              conversations[convIndex] = updatedConv;
              return {
                messages,
                conversations,
              };
            }
          }
          return { messages };
        });
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

      const currentId = state.currentConversationId;
      if (currentId) {
        const convIndex = state.conversations.findIndex(c => c.id === currentId);
        if (convIndex !== -1) {
          const conversations = [...state.conversations];
          conversations[convIndex] = {
            ...conversations[convIndex],
            messages,
            updatedAt: new Date(),
          };
          return { messages, conversations };
        }
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

  setCurrentModel: (model) => set({ currentModel: model }),

  loadConversation: (conversationId) => {
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
    const id = crypto.randomUUID();
    const now = new Date();
    const conv: Conversation = {
      id,
      title: 'New Chat',
      messages: [],
      model: get().currentModel,
      createdAt: now,
      updatedAt: now,
    };
    set((state) => ({
      conversations: [conv, ...state.conversations],
      currentConversationId: id,
      messages: [],
    }));
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

  getContext: () => {
    const MAX_CONTEXT_TURNS = 6;
    const { messages, conversations, currentConversationId } = get();
    const conv = conversations.find(c => c.id === currentConversationId);
    const start = conv?.contextStartIndex ?? 0;
    const slice = messages.slice(start);
    const core = slice.filter(m => m.role === 'user' || m.role === 'assistant');
    const tail = core.slice(-MAX_CONTEXT_TURNS * 2);
    return tail;
  },

  resetContext: () => {
    const { currentConversationId, conversations, messages } = get();
    if (currentConversationId) {
      const convIndex = conversations.findIndex(c => c.id === currentConversationId);
      if (convIndex !== -1) {
        const convs = [...conversations];
        convs[convIndex] = {
          ...convs[convIndex],
          contextStartIndex: messages.length,
        };
        set({ conversations: convs });
      }
    }
  },

  getContextTokens: () => {
    const ctx = get().getContext();
    const estimateTokens = (text: string): number => {
      const words = text.match(/\S+/g)?.length || 0;
      return Math.ceil(words * 1.3);
    };
    return ctx.reduce((sum, m) => sum + estimateTokens(m.content), 0);
  },
    }),
    {
      name: 'aetherai-chat-session',
      // Store only messages and model for free tier session memory
      partialize: (state) => ({
        messages: state.messages,
        currentModel: state.currentModel,
        currentConversationId: state.currentConversationId,
        conversations: state.conversations
      })
    }
  )
);
