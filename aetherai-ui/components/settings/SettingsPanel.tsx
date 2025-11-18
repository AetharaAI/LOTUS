/**
 * Settings Panel Component
 *
 * Shows user tier, feature toggles, and upgrade prompts.
 */

'use client';

import { useState } from 'react';
import { useSettingsStore, type UserTier, type Feature } from '@/lib/stores/settingsStore';

export function SettingsPanel() {
  const [isOpen, setIsOpen] = useState(false);
  const { userTier, features, setUserTier, toggleFeature, isFeatureAvailable } = useSettingsStore();

  const featuresByCategory = {
    memory: Object.values(features).filter(f => f.category === 'memory'),
    execution: Object.values(features).filter(f => f.category === 'execution'),
    perception: Object.values(features).filter(f => f.category === 'perception'),
    advanced: Object.values(features).filter(f => f.category === 'advanced')
  };

  return (
    <>
      {/* Floating Settings Button */}
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-6 right-6 p-4 bg-purple-600 hover:bg-purple-700 rounded-full shadow-lg transition-all duration-200 z-40"
        aria-label="Settings"
      >
        <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
      </button>

      {/* Settings Modal */}
      {isOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-80 flex items-center justify-center z-50 p-4">
          <div className="bg-slate-900 rounded-lg max-w-4xl w-full max-h-[90vh] overflow-y-auto border border-purple-500/30">
            {/* Header */}
            <div className="sticky top-0 bg-slate-900 border-b border-purple-500/30 p-6 flex justify-between items-center">
              <h2 className="text-2xl font-bold text-purple-300">AetherAI Settings</h2>
              <button
                onClick={() => setIsOpen(false)}
                className="text-gray-400 hover:text-white transition-colors"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Content */}
            <div className="p-6 space-y-8">
              {/* Tier Selection */}
              <div>
                <h3 className="text-xl font-semibold text-white mb-4">Your Tier</h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <TierCard
                    tier="basic"
                    title="Basic"
                    price="Free"
                    description="Model Triad with smart routing"
                    features={[
                      'Apriel, Grok & Claude',
                      'Intelligent routing',
                      'SSE streaming',
                      'Session memory (browser)'
                    ]}
                    isActive={userTier === 'basic'}
                    onSelect={() => setUserTier('basic')}
                  />
                  <TierCard
                    tier="pro"
                    title="Pro"
                    price="$9.99/mo"
                    description="+ Conversation persistence"
                    features={[
                      'Everything in Basic',
                      '7-day conversation history',
                      'L1 + L2 memory',
                      'Cross-device sync'
                    ]}
                    isActive={userTier === 'pro'}
                    onSelect={() => setUserTier('pro')}
                  />
                  <TierCard
                    tier="power"
                    title="Power"
                    price="$29.99/mo"
                    description="Full LOTUS orchestration"
                    features={[
                      'Everything in Pro',
                      'Full 4-tier memory',
                      'Parallel execution',
                      'Perception module',
                      'Autonomous agents'
                    ]}
                    isActive={userTier === 'power'}
                    onSelect={() => setUserTier('power')}
                  />
                </div>
              </div>

              {/* Feature Toggles */}
              <div>
                <h3 className="text-xl font-semibold text-white mb-4">Features</h3>

                {/* Memory Features */}
                <FeatureCategory
                  title="Memory"
                  features={featuresByCategory.memory}
                  userTier={userTier}
                  isFeatureAvailable={isFeatureAvailable}
                  toggleFeature={toggleFeature}
                />

                {/* Execution Features */}
                <FeatureCategory
                  title="Execution"
                  features={featuresByCategory.execution}
                  userTier={userTier}
                  isFeatureAvailable={isFeatureAvailable}
                  toggleFeature={toggleFeature}
                />

                {/* Perception Features */}
                <FeatureCategory
                  title="Perception"
                  features={featuresByCategory.perception}
                  userTier={userTier}
                  isFeatureAvailable={isFeatureAvailable}
                  toggleFeature={toggleFeature}
                />

                {/* Advanced Features */}
                <FeatureCategory
                  title="Advanced"
                  features={featuresByCategory.advanced}
                  userTier={userTier}
                  isFeatureAvailable={isFeatureAvailable}
                  toggleFeature={toggleFeature}
                />
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

interface TierCardProps {
  tier: UserTier;
  title: string;
  price: string;
  description: string;
  features: string[];
  isActive: boolean;
  onSelect: () => void;
}

function TierCard({ tier, title, price, description, features, isActive, onSelect }: TierCardProps) {
  return (
    <div
      onClick={onSelect}
      className={`p-6 rounded-lg border-2 cursor-pointer transition-all duration-200 ${
        isActive
          ? 'border-purple-500 bg-purple-900/20'
          : 'border-slate-700 hover:border-purple-500/50 bg-slate-800/50'
      }`}
    >
      <div className="flex justify-between items-start mb-2">
        <h4 className="text-lg font-bold text-white">{title}</h4>
        {isActive && (
          <span className="px-2 py-1 bg-purple-600 text-xs rounded text-white">Active</span>
        )}
      </div>
      <p className="text-2xl font-bold text-purple-400 mb-2">{price}</p>
      <p className="text-sm text-gray-400 mb-4">{description}</p>
      <ul className="space-y-2">
        {features.map((feature, index) => (
          <li key={index} className="flex items-start text-sm text-gray-300">
            <svg className="w-5 h-5 text-purple-500 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
            {feature}
          </li>
        ))}
      </ul>
    </div>
  );
}

interface FeatureCategoryProps {
  title: string;
  features: Feature[];
  userTier: UserTier;
  isFeatureAvailable: (featureId: string) => boolean;
  toggleFeature: (featureId: string) => void;
}

function FeatureCategory({ title, features, userTier, isFeatureAvailable, toggleFeature }: FeatureCategoryProps) {
  if (features.length === 0) return null;

  return (
    <div className="mb-6">
      <h4 className="text-lg font-semibold text-purple-400 mb-3">{title}</h4>
      <div className="space-y-2">
        {features.map((feature) => {
          const available = isFeatureAvailable(feature.id);
          return (
            <div
              key={feature.id}
              className="flex items-center justify-between p-4 bg-slate-800/50 rounded-lg border border-slate-700"
            >
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <p className="font-medium text-white">{feature.name}</p>
                  {!available && (
                    <span className="px-2 py-0.5 bg-purple-900/50 text-purple-300 text-xs rounded border border-purple-500/50">
                      {feature.requiredTier.toUpperCase()}
                    </span>
                  )}
                </div>
                <p className="text-sm text-gray-400 mt-1">{feature.description}</p>
              </div>
              <div className="ml-4">
                {available ? (
                  <button
                    onClick={() => toggleFeature(feature.id)}
                    className={`w-12 h-6 rounded-full transition-colors duration-200 ${
                      feature.enabled ? 'bg-purple-600' : 'bg-gray-600'
                    }`}
                  >
                    <div
                      className={`w-5 h-5 rounded-full bg-white transition-transform duration-200 ${
                        feature.enabled ? 'translate-x-6' : 'translate-x-0.5'
                      }`}
                    />
                  </button>
                ) : (
                  <button className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white text-sm rounded transition-colors duration-200">
                    Upgrade
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
