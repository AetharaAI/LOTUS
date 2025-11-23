import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // Deep Space Purple Palette (AetherAI Brand)
        'aether-purple-darkest': '#0a0515',
        'aether-purple-dark': '#1a0b2e',
        'aether-purple-mid': '#2d1b4e',
        'aether-purple-light': '#4a2c6d',
        'aether-purple-accent': '#6b4a8e',

        // High Voltage Orange (Brand Accent)
        'aether-orange': '#ff6b35',
        'aether-orange-glow': '#ff8555',
        'aether-orange-dark': '#cc5529',

        // Industrial Neutrals
        'aether-steel': '#8892b0',
        'aether-graphite': '#1e1e2e',
        'aether-white': '#e6f1ff',
        'aether-text': '#e6f1ff',
        'aether-text-muted': '#a8b2d1',

        // Semantic Colors (mapped to palette)
        'aether-bg-dark': '#0a0515',      // Darkest purple
        'aether-bg-card': '#1a0b2e',       // Dark purple
        'aether-bg-hover': '#2d1b4e',      // Mid purple

        // Borders
        'aether-border': '#2d1b4e',
        'aether-border-light': '#4a2c6d',

        // Legacy alias (for components using old naming)
        'aether-indigo-light': '#4a2c6d',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Menlo', 'Consolas', 'monospace'],
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
    },
  },
  plugins: [],
};

export default config;
