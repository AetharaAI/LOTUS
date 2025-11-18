/**
 * Profile Button Component
 *
 * Optional login button in bottom-left corner (ChatGPT style).
 * No login required - users can chat immediately.
 */

'use client';

import { useState } from 'react';
import { useAuthStore } from '@/lib/stores/authStore';

export function ProfileButton() {
  const [showMenu, setShowMenu] = useState(false);
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [authMode, setAuthMode] = useState<'login' | 'register'>('login');
  const { user, isAuthenticated, login, register, logout } = useAuthStore();

  const handleLogin = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const email = formData.get('email') as string;
    const password = formData.get('password') as string;

    try {
      await login(email, password);
      setShowAuthModal(false);
    } catch (error) {
      console.error('Login failed:', error);
      alert('Login failed. Please try again.');
    }
  };

  const handleRegister = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const email = formData.get('email') as string;
    const password = formData.get('password') as string;
    const name = formData.get('name') as string;

    try {
      await register(email, password, name);
      setShowAuthModal(false);
    } catch (error) {
      console.error('Registration failed:', error);
      alert('Registration failed. Please try again.');
    }
  };

  return (
    <>
      {/* Profile Button (Bottom-Left) */}
      <div className="fixed bottom-6 left-6 z-40">
        {isAuthenticated ? (
          <div className="relative">
            <button
              onClick={() => setShowMenu(!showMenu)}
              className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg transition-colors duration-200"
            >
              <div className="w-8 h-8 rounded-full bg-purple-600 flex items-center justify-center text-white font-semibold">
                {user?.name?.[0]?.toUpperCase() || user?.email?.[0]?.toUpperCase() || 'U'}
              </div>
              <div className="text-left">
                <p className="text-sm text-white font-medium">{user?.name || 'User'}</p>
                <p className="text-xs text-purple-400">{user?.tier.toUpperCase()}</p>
              </div>
            </button>

            {/* Profile Menu */}
            {showMenu && (
              <div className="absolute bottom-full left-0 mb-2 w-48 bg-slate-800 border border-slate-700 rounded-lg shadow-lg overflow-hidden">
                <div className="p-3 border-b border-slate-700">
                  <p className="text-sm text-white font-medium truncate">{user?.email}</p>
                </div>
                <button
                  onClick={() => {
                    /* TODO: Open settings */
                    setShowMenu(false);
                  }}
                  className="w-full px-3 py-2 text-left text-sm text-gray-300 hover:bg-slate-700 transition-colors"
                >
                  Settings & Billing
                </button>
                <button
                  onClick={() => {
                    logout();
                    setShowMenu(false);
                  }}
                  className="w-full px-3 py-2 text-left text-sm text-red-400 hover:bg-slate-700 transition-colors"
                >
                  Sign out
                </button>
              </div>
            )}
          </div>
        ) : (
          <button
            onClick={() => setShowAuthModal(true)}
            className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors duration-200"
          >
            Sign in
          </button>
        )}
      </div>

      {/* Auth Modal */}
      {showAuthModal && (
        <div className="fixed inset-0 bg-black bg-opacity-80 flex items-center justify-center z-50 p-4">
          <div className="bg-slate-900 rounded-lg max-w-md w-full border border-purple-500/30">
            {/* Header */}
            <div className="p-6 border-b border-purple-500/30 flex justify-between items-center">
              <h2 className="text-2xl font-bold text-purple-300">
                {authMode === 'login' ? 'Sign In' : 'Create Account'}
              </h2>
              <button
                onClick={() => setShowAuthModal(false)}
                className="text-gray-400 hover:text-white transition-colors"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Content */}
            <div className="p-6">
              <p className="text-sm text-gray-400 mb-6">
                {authMode === 'login'
                  ? 'Sign in to save your conversations across devices'
                  : 'Create an account to unlock Pro features'}
              </p>

              {authMode === 'login' ? (
                <form onSubmit={handleLogin} className="space-y-4">
                  <div>
                    <label htmlFor="email" className="block text-sm font-medium text-gray-300 mb-2">
                      Email
                    </label>
                    <input
                      type="email"
                      id="email"
                      name="email"
                      required
                      className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:border-purple-500 focus:outline-none"
                      placeholder="you@example.com"
                    />
                  </div>

                  <div>
                    <label htmlFor="password" className="block text-sm font-medium text-gray-300 mb-2">
                      Password
                    </label>
                    <input
                      type="password"
                      id="password"
                      name="password"
                      required
                      className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:border-purple-500 focus:outline-none"
                      placeholder="••••••••"
                    />
                  </div>

                  <button
                    type="submit"
                    className="w-full px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors duration-200"
                  >
                    Sign In
                  </button>
                </form>
              ) : (
                <form onSubmit={handleRegister} className="space-y-4">
                  <div>
                    <label htmlFor="name" className="block text-sm font-medium text-gray-300 mb-2">
                      Name (optional)
                    </label>
                    <input
                      type="text"
                      id="name"
                      name="name"
                      className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:border-purple-500 focus:outline-none"
                      placeholder="Your name"
                    />
                  </div>

                  <div>
                    <label htmlFor="reg-email" className="block text-sm font-medium text-gray-300 mb-2">
                      Email
                    </label>
                    <input
                      type="email"
                      id="reg-email"
                      name="email"
                      required
                      className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:border-purple-500 focus:outline-none"
                      placeholder="you@example.com"
                    />
                  </div>

                  <div>
                    <label htmlFor="reg-password" className="block text-sm font-medium text-gray-300 mb-2">
                      Password
                    </label>
                    <input
                      type="password"
                      id="reg-password"
                      name="password"
                      required
                      className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:border-purple-500 focus:outline-none"
                      placeholder="••••••••"
                    />
                  </div>

                  <button
                    type="submit"
                    className="w-full px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors duration-200"
                  >
                    Create Account
                  </button>
                </form>
              )}

              <div className="mt-6 text-center">
                <button
                  onClick={() => setAuthMode(authMode === 'login' ? 'register' : 'login')}
                  className="text-sm text-purple-400 hover:text-purple-300 transition-colors"
                >
                  {authMode === 'login'
                    ? "Don't have an account? Sign up"
                    : 'Already have an account? Sign in'}
                </button>
              </div>

              <p className="mt-4 text-xs text-gray-500 text-center">
                No account needed to use AetherAI
              </p>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
