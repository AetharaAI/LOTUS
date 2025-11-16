import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        aether: {
          // Sharp Purple Gradient - Use EVERYWHERE brand appears
          'purple-dark': '#6d28d9',
          'purple-light': '#8b5cf6',

          // Deep Indigo - Foundation
          'indigo': '#1e1b4b',
          'indigo-dark': '#0f0d2e',
          'indigo-light': '#312e81',

          // Backgrounds
          'bg-dark': '#0a0a0f',
          'bg-card': '#1a1625',
          'bg-hover': '#251d35',

          // Text
          'text': '#e2e8f0',
          'text-muted': '#94a3b8',
          'text-dark': '#0f172a',

          // Accents (minimal use)
          'orange-spark': '#ff6b35',
          'gold': '#d4af37',
        },
      },
      fontFamily: {
        sans: ['Outfit', 'Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      animation: {
        'pulse-glow': 'pulse-glow 2s ease-in-out infinite',
        'fade-in': 'fade-in 0.3s ease-out',
        'slide-up': 'slide-up 0.3s ease-out',
      },
      keyframes: {
        'pulse-glow': {
          '0%, 100%': {
            textShadow: '0 0 20px rgba(109, 40, 217, 0.8)',
          },
          '50%': {
            textShadow: '0 0 40px rgba(109, 40, 217, 1)',
          },
        },
        'fade-in': {
          from: { opacity: '0' },
          to: { opacity: '1' },
        },
        'slide-up': {
          from: {
            opacity: '0',
            transform: 'translateY(10px)',
          },
          to: {
            opacity: '1',
            transform: 'translateY(0)',
          },
        },
      },
      backgroundImage: {
        'gradient-aether': 'linear-gradient(135deg, #6d28d9, #8b5cf6)',
        'gradient-aether-indigo': 'linear-gradient(135deg, #312e81, #6d28d9)',
      },
    },
  },
  plugins: [],
};

export default config;
