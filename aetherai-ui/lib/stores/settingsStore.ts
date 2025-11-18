/**
 * Settings Store
 *
 * Manages user tier, feature flags, and system settings.
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export type UserTier = 'basic' | 'pro' | 'power';

export interface Feature {
  id: string;
  name: string;
  description: string;
  requiredTier: UserTier;
  enabled: boolean;
  category: 'memory' | 'execution' | 'perception' | 'advanced';
}

interface SettingsState {
  // User tier
  userTier: UserTier;

  // Feature flags
  features: Record<string, Feature>;

  // Actions
  setUserTier: (tier: UserTier) => void;
  toggleFeature: (featureId: string) => void;
  isFeatureAvailable: (featureId: string) => boolean;
}

// Define all features
const defaultFeatures: Record<string, Feature> = {
  'conversation-memory': {
    id: 'conversation-memory',
    name: 'Conversation Memory',
    description: 'Save conversations across sessions (7 days)',
    requiredTier: 'pro',
    enabled: false,
    category: 'memory'
  },
  'long-term-memory': {
    id: 'long-term-memory',
    name: 'Long-Term Memory (L3)',
    description: 'Semantic memory search with ChromaDB',
    requiredTier: 'power',
    enabled: false,
    category: 'memory'
  },
  'persistent-memory': {
    id: 'persistent-memory',
    name: 'Persistent Memory (L4)',
    description: 'Permanent knowledge storage in PostgreSQL',
    requiredTier: 'power',
    enabled: false,
    category: 'memory'
  },
  'parallel-execution': {
    id: 'parallel-execution',
    name: 'Parallel Execution',
    description: 'Run multiple tasks concurrently',
    requiredTier: 'power',
    enabled: false,
    category: 'execution'
  },
  'tool-use': {
    id: 'tool-use',
    name: 'Tool Use & Reasoning',
    description: 'Enable ReasoningEngine with tool execution',
    requiredTier: 'power',
    enabled: false,
    category: 'execution'
  },
  'perception-module': {
    id: 'perception-module',
    name: 'Perception Module',
    description: 'Screen and clipboard monitoring',
    requiredTier: 'power',
    enabled: false,
    category: 'perception'
  },
  'autonomous-agents': {
    id: 'autonomous-agents',
    name: 'Autonomous Agents',
    description: 'Deploy autonomous AI agents',
    requiredTier: 'power',
    enabled: false,
    category: 'advanced'
  },
  'multi-model-orchestration': {
    id: 'multi-model-orchestration',
    name: 'Multi-Model Orchestration',
    description: 'Advanced model routing and blending',
    requiredTier: 'power',
    enabled: false,
    category: 'advanced'
  }
};

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set, get) => ({
      // Initial state
      userTier: 'basic',
      features: defaultFeatures,

      // Set user tier
      setUserTier: (tier) => {
        set({ userTier: tier });

        // Sync to authStore if available
        if (typeof window !== 'undefined') {
          try {
            const { useAuthStore } = require('./authStore');
            const authState = useAuthStore.getState();
            if (authState.user) {
              authState.user.tier = tier;
            }
          } catch (e) {
            // authStore not available yet
          }
        }

        // Auto-enable/disable features based on tier
        const features = { ...get().features };
        Object.keys(features).forEach(featureId => {
          const feature = features[featureId];
          const tierLevels: Record<UserTier, number> = { basic: 0, pro: 1, power: 2 };
          const available = tierLevels[tier] >= tierLevels[feature.requiredTier];
          features[featureId].enabled = available;
        });
        set({ features });
      },

      // Toggle feature
      toggleFeature: (featureId) => {
        const features = { ...get().features };
        if (features[featureId] && get().isFeatureAvailable(featureId)) {
          features[featureId].enabled = !features[featureId].enabled;
          set({ features });
        }
      },

      // Check if feature is available for current tier
      isFeatureAvailable: (featureId) => {
        const feature = get().features[featureId];
        if (!feature) return false;

        const tierLevels: Record<UserTier, number> = { basic: 0, pro: 1, power: 2 };
        return tierLevels[get().userTier] >= tierLevels[feature.requiredTier];
      }
    }),
    {
      name: 'aetherai-settings'
    }
  )
);
