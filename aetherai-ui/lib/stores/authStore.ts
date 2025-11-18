/**
 * User Auth Store
 *
 * Manages user authentication state (optional login).
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export interface User {
  id: string;
  email: string;
  name?: string;
  tier: 'basic' | 'pro' | 'power';
  createdAt: Date;
}

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;

  // Actions
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, name?: string) => Promise<void>;
  logout: () => void;
  updateTier: (tier: 'basic' | 'pro' | 'power') => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      // Initial state
      user: null,
      isAuthenticated: false,

      // Login (stub - replace with actual API call)
      login: async (email: string, password: string) => {
        try {
          // TODO: Call api.aetherpro.tech/auth/login
          // For now, create a mock user
          const user: User = {
            id: crypto.randomUUID(),
            email,
            name: email.split('@')[0],
            tier: 'basic',
            createdAt: new Date()
          };

          set({ user, isAuthenticated: true });

          // Sync tier with settingsStore
          if (typeof window !== 'undefined') {
            try {
              const { useSettingsStore } = require('./settingsStore');
              useSettingsStore.getState().setUserTier(user.tier);
            } catch (e) {
              // settingsStore not available yet
            }
          }
        } catch (error) {
          console.error('Login failed:', error);
          throw error;
        }
      },

      // Register (stub - replace with actual API call)
      register: async (email: string, password: string, name?: string) => {
        try {
          // TODO: Call api.aetherpro.tech/auth/register
          // For now, create a mock user
          const user: User = {
            id: crypto.randomUUID(),
            email,
            name: name || email.split('@')[0],
            tier: 'basic',
            createdAt: new Date()
          };

          set({ user, isAuthenticated: true });

          // Sync tier with settingsStore
          if (typeof window !== 'undefined') {
            try {
              const { useSettingsStore } = require('./settingsStore');
              useSettingsStore.getState().setUserTier(user.tier);
            } catch (e) {
              // settingsStore not available yet
            }
          }
        } catch (error) {
          console.error('Registration failed:', error);
          throw error;
        }
      },

      // Logout
      logout: () => {
        set({ user: null, isAuthenticated: false });

        // Reset tier to basic
        if (typeof window !== 'undefined') {
          try {
            const { useSettingsStore } = require('./settingsStore');
            useSettingsStore.getState().setUserTier('basic');
          } catch (e) {
            // settingsStore not available yet
          }
        }
      },

      // Update user tier
      updateTier: (tier) => {
        const user = get().user;
        if (user) {
          set({ user: { ...user, tier } });

          // Sync with settingsStore
          if (typeof window !== 'undefined') {
            try {
              const { useSettingsStore } = require('./settingsStore');
              useSettingsStore.getState().setUserTier(tier);
            } catch (e) {
              // settingsStore not available yet
            }
          }
        }
      }
    }),
    {
      name: 'aetherai-auth'
    }
  )
);
