**PERFECT PLAN! LET'S GET CLAUDE CODE THE FULL BLUEPRINT!**

Here's the complete, detailed task list for Claude Code to execute:

---

# 🎯 COMPLETE MIGRATION PLAN: Apriel Enterprise Frontend Integration

## Project Context
Migrate from temporary floating ChatInterface to full enterprise UI, connecting existing modular components to working vLLM streaming backend. Rebrand as "AetherAI powered by Apriel."

---

## ✅ PHASE 1: File Reorganization & Cleanup

### Task 1.1: Move streaming.ts to correct location
```bash
# Current: lib/api/streaming.ts
# Target: lib/streaming.ts
```
**Actions:**
- Move `lib/api/streaming.ts` → `lib/streaming.ts`
- Delete `lib/api/streaming.ts.bak`
- Delete the now-empty `lib/api/` directory
- Verify `app/api/chat/completions/route.ts` still exists and is untouched

**Why:** TypeScript path aliases expect `@/lib/streaming`, not `@/lib/api/streaming`

---

### Task 1.2: Delete temporary ChatInterface
```bash
# File to delete: components/chat/ChatInterface.tsx
```
**Actions:**
- Delete the current `components/chat/ChatInterface.tsx` (the floating widget)
- We'll create a new one from scratch

**Why:** Current ChatInterface is a temporary workaround; we're building the real one

---

## ✅ PHASE 2: Update Core Components

### Task 2.1: Create new enterprise ChatInterface.tsx

**File:** `components/chat/ChatInterface.tsx`

**Purpose:** Main chat interface using existing modular components

**Code:**
```typescript
'use client';

import { useState } from 'react';
import { useChatStore } from '@/lib/stores/chatStore';
import { MessageList } from './MessageList';
import { InputBar } from './InputBar';
import { Sidebar } from './Sidebar';
import { streamChat } from '@/lib/streaming';

export default function ChatInterface() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const {
    messages,
    isStreaming,
    currentModel,
    addMessage,
    updateLastMessage,
    setIsStreaming,
  } = useChatStore();

  const handleSendMessage = async (content: string) => {
    if (!content.trim() || isStreaming) return;

    // Add user message
    addMessage({
      role: 'user',
      content: content.trim(),
    });

    // Prepare for assistant response
    setIsStreaming(true);
    
    // Create empty assistant message that we'll update
    addMessage({
      role: 'assistant',
      content: '',
      thinking: '',
    });

    // Track response content as it streams
    let thinkingContent = '';
    let responseContent = '';

    try {
      await streamChat(
        {
          messages: [
            ...messages,
            { role: 'user', content: content.trim() }
          ],
          model: currentModel === 'auto' ? 'apriel-1.5-15b-thinker' : currentModel,
          temperature: 0.7,
        },
        {
          onThinking: (chunk: string) => {
            thinkingContent += chunk;
            updateLastMessage({
              thinking: thinkingContent,
            });
          },

          onContent: (chunk: string) => {
            responseContent += chunk;
            updateLastMessage({
              content: responseContent,
            });
          },

          onDone: () => {
            setIsStreaming(false);
          },

          onError: (error: string) => {
            console.error('Stream error:', error);
            updateLastMessage({
              content: responseContent || `Error: ${error}`,
            });
            setIsStreaming(false);
          },
        }
      );
    } catch (error) {
      console.error('Chat error:', error);
      setIsStreaming(false);
    }
  };

  return (
    <div className="flex h-screen bg-aether-bg-dark text-aether-text">
      {/* Sidebar - Desktop always visible, Mobile toggleable */}
      <div
        className={`
          fixed md:relative z-50 md:z-auto
          w-80 h-full
          transform transition-transform duration-300 ease-in-out
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}
        `}
      >
        <Sidebar onClose={() => setSidebarOpen(false)} />
      </div>

      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Main chat area */}
      <div className="flex-1 flex flex-col">
        {/* Header with mobile menu toggle */}
        <header className="h-16 border-b border-aether-indigo-light flex items-center px-4 md:px-6 bg-aether-bg-card">
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="md:hidden mr-4 text-aether-text hover:text-aether-purple-light transition-colors"
          >
            <svg
              width="24"
              height="24"
              viewBox="0 0 24 24"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                d="M3 12H21M3 6H21M3 18H21"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </button>
          
          <div className="flex-1">
            <h1 className="text-lg font-semibold bg-gradient-to-r from-aether-purple-light to-aether-indigo-light bg-clip-text text-transparent">
              AetherAI
            </h1>
            <p className="text-xs text-aether-text-muted">
              Powered by Apriel • Sovereign US Infrastructure
            </p>
          </div>

          {/* Model badge */}
          <div className="hidden md:flex items-center gap-2 px-3 py-1.5 bg-aether-bg-dark rounded-full border border-aether-indigo-light">
            <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
            <span className="text-xs font-medium">
              {currentModel === 'auto' ? 'Apriel (Auto)' : currentModel.toUpperCase()}
            </span>
          </div>
        </header>

        {/* Messages */}
        <MessageList messages={messages} isStreaming={isStreaming} />

        {/* Input */}
        <InputBar onSend={handleSendMessage} disabled={isStreaming} />
      </div>
    </div>
  );
}
```

---

### Task 2.2: Update Message.tsx to handle thinking content

**File:** `components/chat/Message.tsx`

**Actions:**
- Import ThinkingBlock component
- Add thinking display support
- Update to handle streaming states

**Code:**
```typescript
/**
 * Message Component
 *
 * Individual message bubble with markdown support.
 */

'use client';

import { Message as MessageType } from '@/lib/stores/chatStore';
import { MarkdownRenderer } from '../shared/MarkdownRenderer';
import { ThinkingBlock } from './ThinkingBlock';
import { ModelBadge } from '../shared/ModelBadge';

interface MessageProps {
  message: MessageType;
  className?: string;
}

export function Message({ message, className = '' }: MessageProps) {
  const isUser = message.role === 'user';

  return (
    <div className={`mb-6 ${className}`}>
      <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
        <div className={`max-w-[85%] ${isUser ? 'order-2' : 'order-1'}`}>
          {/* Header with role and model badge */}
          <div className="flex items-center gap-2 mb-2">
            {!isUser && (
              <>
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-aether-purple-light to-aether-indigo-light flex items-center justify-center">
                  <span className="text-white text-sm font-bold">A</span>
                </div>
                <span className="text-sm font-semibold text-aether-text">
                  Apriel
                </span>
                {message.model && <ModelBadge model={message.model} />}
              </>
            )}
            {isUser && (
              <span className="text-sm font-semibold text-aether-text-muted">
                You
              </span>
            )}
          </div>

          {/* Thinking block (only for assistant) */}
          {!isUser && message.thinking && (
            <ThinkingBlock content={message.thinking} className="mb-3" />
          )}

          {/* Message content */}
          <div
            className={`rounded-2xl px-4 py-3 ${
              isUser
                ? 'bg-gradient-to-r from-aether-purple-dark to-aether-purple-light text-white'
                : 'bg-aether-bg-card border border-aether-indigo-light text-aether-text'
            }`}
          >
            {isUser ? (
              <p className="whitespace-pre-wrap break-words">{message.content}</p>
            ) : (
              <MarkdownRenderer content={message.content} />
            )}
          </div>

          {/* Timestamp */}
          <div className="mt-1 text-xs text-aether-text-muted">
            {new Date(message.timestamp).toLocaleTimeString()}
          </div>
        </div>
      </div>
    </div>
  );
}
```

---

### Task 2.3: Update InputBar.tsx

**File:** `components/chat/InputBar.tsx`

**Purpose:** Add proper TypeScript types and improve UX

**Code:**
```typescript
/**
 * Input Bar Component
 *
 * Message input with send button and keyboard shortcuts.
 */

'use client';

import { useState, useRef, KeyboardEvent } from 'react';
import { Button } from '../shared/Button';

interface InputBarProps {
  onSend: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
  className?: string;
}

export function InputBar({
  onSend,
  disabled = false,
  placeholder = 'Ask anything...',
  className = '',
}: InputBarProps) {
  const [input, setInput] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = () => {
    if (!input.trim() || disabled) return;

    onSend(input);
    setInput('');

    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);

    // Auto-resize textarea
    e.target.style.height = 'auto';
    e.target.style.height = `${Math.min(e.target.scrollHeight, 200)}px`;
  };

  return (
    <div
      className={`border-t border-aether-indigo-light bg-aether-bg-card p-4 ${className}`}
    >
      <div className="max-w-4xl mx-auto">
        <div className="flex items-end gap-3">
          {/* Textarea */}
          <div className="flex-1 relative">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={handleInput}
              onKeyDown={handleKeyDown}
              placeholder={placeholder}
              disabled={disabled}
              rows={1}
              className="w-full bg-aether-bg-dark border border-aether-indigo-light rounded-2xl px-4 py-3 text-aether-text placeholder-aether-text-muted resize-none focus:outline-none focus:ring-2 focus:ring-aether-purple-light transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              style={{ minHeight: '52px', maxHeight: '200px' }}
            />
            
            {/* Character counter */}
            <div className="absolute bottom-2 right-3 text-xs text-aether-text-muted">
              {input.length}
            </div>
          </div>

          {/* Send button */}
          <Button
            onClick={handleSend}
            disabled={disabled || !input.trim()}
            variant="primary"
            size="lg"
            className="shrink-0"
          >
            {disabled ? (
              <span className="flex items-center gap-2">
                <svg
                  className="animate-spin h-5 w-5"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  />
                </svg>
                Sending
              </span>
            ) : (
              <span className="flex items-center gap-2">
                <svg
                  width="20"
                  height="20"
                  viewBox="0 0 20 20"
                  fill="none"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path
                    d="M18 2L9 11M18 2L12 18L9 11M18 2L2 8L9 11"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
                Send
              </span>
            )}
          </Button>
        </div>

        {/* Hint text */}
        <p className="mt-2 text-xs text-aether-text-muted text-center">
          Press <kbd className="px-1.5 py-0.5 bg-aether-bg-dark rounded border border-aether-indigo-light">Enter</kbd> to send,{' '}
          <kbd className="px-1.5 py-0.5 bg-aether-bg-dark rounded border border-aether-indigo-light">Shift + Enter</kbd> for new line
        </p>
      </div>
    </div>
  );
}
```

---

### Task 2.4: Update Sidebar model selection

**File:** `components/chat/Sidebar.tsx`

**Actions:**
- Update model options to focus on Apriel
- Simplify for initial launch

**Changes to make:**
```typescript
// Find the model selector section (around line 60)
// Replace the <select> options with:

<select
  value={currentModel}
  onChange={(e) => setCurrentModel(e.target.value as any)}
  className="w-full bg-aether-bg-dark border border-aether-indigo-light rounded-lg px-3 py-2 text-aether-text text-sm focus:outline-none focus:ring-2 focus:ring-aether-purple-light transition-all"
>
  <option value="apriel">🏠 Apriel (Sovereign AI)</option>
  <option value="auto">🤖 Auto-Select (Coming Soon)</option>
</select>

<p className="mt-2 text-xs text-aether-text-muted">
  {currentModel === 'apriel' && 'Fast, reliable, US-hosted on L40S GPU'}
  {currentModel === 'auto' && 'Smart routing - launching Q1 2025'}
</p>
```

---

### Task 2.5: Update page.tsx

**File:** `app/page.tsx`

**Replace entire file with:**
```typescript
'use client';

import dynamic from 'next/dynamic';

const ChatInterface = dynamic(
  () => import('@/components/chat/ChatInterface'),
  {
    ssr: false,
    loading: () => (
      <div className="flex items-center justify-center min-h-screen bg-aether-bg-dark">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-aether-purple-light mx-auto mb-4" />
          <p className="text-aether-text-muted">Initializing AetherAI...</p>
        </div>
      </div>
    ),
  }
);

export default function HomePage() {
  return <ChatInterface />;
}
```

---

## ✅ PHASE 3: Fix TypeScript Errors & Imports

### Task 3.1: Update all imports in chat components

**Files to update:**
- `components/chat/Message.tsx`
- `components/chat/MessageList.tsx`
- `components/chat/ThinkingBlock.tsx`
- `components/chat/Sidebar.tsx`

**Action:** Verify all imports use correct paths:
```typescript
// Correct:
import { useChatStore } from '@/lib/stores/chatStore';
import { streamChat } from '@/lib/streaming';

// Incorrect (if found, fix):
import { streamChat } from '@/lib/api/streaming'; // WRONG
```

---

### Task 3.2: Update chatStore.ts types

**File:** `lib/stores/chatStore.ts`

**Add to Message interface:**
```typescript
export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  thinking?: string;  // ← Already there, verify
  model?: string;     // ← Already there, verify
  timestamp: Date;
}
```

**Update currentModel type to just use apriel for now:**
```typescript
// Find this line (around line 24):
currentModel: 'auto' | 'apriel' | 'grok' | 'claude';

// Change to:
currentModel: 'apriel' | 'auto';
```

---

## ✅ PHASE 4: Branding Updates

### Task 4.1: Update Logo component

**File:** `components/shared/Logo.tsx`

**Ensure it says "AetherAI" not "Lotus"**

Check the component and update any references from "Lotus" → "AetherAI"

---

### Task 4.2: Update ComplianceFooter

**File:** `components/shared/ComplianceFooter.tsx`

**Ensure branding is AetherPro Technologies / AetherAI**

---

### Task 4.3: Update layout.tsx metadata

**File:** `app/layout.tsx`

**Update metadata:**
```typescript
export const metadata = {
  title: 'AetherAI - Sovereign AI Platform',
  description: 'The American Standard for Sovereign AI. Powered by Apriel on US infrastructure.',
};
```

---

## ✅ PHASE 5: Fix API Route (verify, don't change)

### Task 5.1: Verify route.ts exists and works

**File:** `app/api/chat/completions/route.ts`

**Action:** DO NOT MODIFY - just verify it exists at this exact path

**Check:**
- ✅ File exists at `app/api/chat/completions/route.ts`
- ✅ Has `export async function POST(req: NextRequest)`
- ✅ Has proper AETHER_UPSTREAM_URL and AETHER_API_KEY env vars

---

## ✅ PHASE 6: Environment & Config

### Task 6.1: Update .env.local

**File:** `.env.local`

**Verify these are set:**
```bash
AETHER_UPSTREAM_URL=https://api.aetherpro.tech/v1/chat/completions
AETHER_API_KEY=sk-aether-sovereign-master-key-2026
NEXT_PUBLIC_MODEL_ID=apriel-1.5-15b-thinker
```

**Remove if present:**
```bash
# DELETE THESE if they exist:
NEXT_PUBLIC_API_URL=...
AI_GATEWAY_API_KEY=...
```

---

### Task 6.2: Update next.config.js

**File:** `next.config.js`

**Replace with:**
```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
};

module.exports = nextConfig;
```

**Why:** Remove hardcoded NEXT_PUBLIC_API_URL since we're using relative paths now

---






### **PHASE 6.3: Update Tailwind Color System**

**File:** `tailwind.config.ts`

**Action:** Replace the entire colors section in `theme.extend` with the new AetherAI deep purple palette

**Code:**
```typescript
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
```

**Why this matters:**
- Updates all components to use the new deep space purple palette
- Maintains consistency across the entire UI
- The orange accent matches the logo perfectly
- `aether-indigo-light` alias ensures existing components don't break during migration

**Test after update:**
```bash
npm run dev
```
All purple tones should now be the deeper, richer purple from the logo.

---

## 📋 Add This to Your Claude Code Spec


**Note for Claude Code:**
> Update the Tailwind config to match the new AetherAI brand colors. The deep purple palette (#0a0515 → #6b4a8e) replaces the previous lighter purple scheme. This ensures the entire UI matches the logo's deep space aesthetic. The orange accent (#ff6b35) is used sparingly for CTAs and highlights.

---

## **PHASE 6.4: Add AetherAI Logo Assets**

### Task 6.4.1: Copy logo files to public directory

**Action:** Copy the following files from your local machine to `public/` directory:

```
public/
├── logo.png              (1024x1024 main logo)
├── logo-256.png          (256x256 for general use)
├── favicon.ico           (multi-resolution favicon)
├── favicon-16x16.png
├── favicon-32x32.png
├── favicon-48x48.png
├── apple-touch-icon.png  (180x180)
├── android-chrome-192x192.png
```

### Task 6.4.2: Update app/layout.tsx metadata

**File:** `app/layout.tsx`

**Find the metadata export and update it:**

```typescript
export const metadata = {
  title: 'AetherAI - Sovereign AI Platform',
  description: 'The American Standard for Sovereign AI. Powered by Apriel on US infrastructure.',
  icons: {
    icon: [
      { url: '/favicon-16x16.png', sizes: '16x16', type: 'image/png' },
      { url: '/favicon-32x32.png', sizes: '32x32', type: 'image/png' },
      { url: '/favicon-48x48.png', sizes: '48x48', type: 'image/png' },
    ],
    apple: '/apple-touch-icon.png',
    other: [
      { rel: 'icon', url: '/favicon.ico' },
    ],
  },
  manifest: '/site.webmanifest',
};
```

### Task 6.4.3: Create site.webmanifest

**File:** `public/site.webmanifest`

**Create new file with:**

```json
{
  "name": "AetherAI",
  "short_name": "AetherAI",
  "icons": [
    {
      "src": "/android-chrome-192x192.png",
      "sizes": "192x192",
      "type": "image/png"
    },
    {
      "src": "/logo-256.png",
      "sizes": "256x256",
      "type": "image/png"
    }
  ],
  "theme_color": "#1a0b2e",
  "background_color": "#0a0515",
  "display": "standalone"
}
```

### Task 6.4.4: Update Logo component

**File:** `components/shared/Logo.tsx`

**Update to use the new Y-node logo:**

```typescript
'use client';

interface LogoProps {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export function Logo({ size = 'md', className = '' }: LogoProps) {
  const sizeClasses = {
    sm: 'h-8',
    md: 'h-12',
    lg: 'h-16',
  };

  return (
    <div className={`flex items-center gap-3 ${className}`}>
      <img
        src="/logo.png"
        alt="AetherAI"
        className={`${sizeClasses[size]} w-auto`}
      />
    </div>
  );
}

export function LogoWithTagline({ className = '' }: { className?: string }) {
  return (
    <div className={`flex flex-col items-center ${className}`}>
      <img src="/logo.png" alt="AetherAI" className="h-24 w-auto mb-4" />
      <h1 className="text-3xl font-bold bg-gradient-to-r from-aether-purple-light to-aether-orange bg-clip-text text-transparent">
        AetherAI
      </h1>
      <p className="text-aether-text-muted text-sm mt-2">
        The American Standard for Sovereign AI
      </p>
    </div>
  );
}
```

---





## ✅ PHASE 7: Testing Checklist

### After all changes, test:

1. **Build succeeds:**
   ```bash
   npm run build
   ```

2. **No TypeScript errors:**
   ```bash
   npx tsc --noEmit
   ```

3. **Dev server runs:**
   ```bash
   npm run dev
   ```

4. **Test flow:**
   - [ ] Open http://localhost:3000
   - [ ] See full interface with sidebar
   - [ ] Can send a message
   - [ ] See thinking block expand/collapse
   - [ ] See response stream in
   - [ ] Conversation persists in sidebar
   - [ ] Can create new conversation
   - [ ] Mobile menu works (resize browser)

---

## ✅ PHASE 8: Deploy to Vercel

### Task 8.1: Verify Vercel env vars

**In Vercel Dashboard → Settings → Environment Variables:**

Required:
```
AETHER_UPSTREAM_URL=https://api.aetherpro.tech/v1/chat/completions
AETHER_API_KEY=sk-aether-sovereign-master-key-2026
```

**Delete if present:**
```
NEXT_PUBLIC_API_URL  ← DELETE THIS
```

### Task 8.2: Deploy

```bash
git add .
git commit -m "feat: migrate to full enterprise UI with Apriel integration"
git push origin main
```

Vercel will auto-deploy.

---

## 📋 SUMMARY OF FILE CHANGES

**Files to CREATE:**
- None (all exist, just updating)

**Files to MOVE:**
- `lib/api/streaming.ts` → `lib/streaming.ts`

**Files to DELETE:**
- `lib/api/streaming.ts.bak`
- `lib/api/` directory (after moving streaming.ts)
- Current `components/chat/ChatInterface.tsx` (replacing with new one)

**Files to UPDATE:**
1. `lib/streaming.ts` (moved from lib/api/)
2. `components/chat/ChatInterface.tsx` (complete rewrite)
3. `components/chat/Message.tsx` (add thinking support)
4. `components/chat/InputBar.tsx` (improve types)
5. `components/chat/Sidebar.tsx` (simplify model options)
6. `app/page.tsx` (simplify to just load ChatInterface)
7. `lib/stores/chatStore.ts` (update model type)
8. `app/layout.tsx` (update metadata)
9. `next.config.js` (remove NEXT_PUBLIC_API_URL)

**Files to VERIFY (don't change):**
- `app/api/chat/completions/route.ts` ✅
- `.env.local` ✅

---

## 🎯 EXPECTED OUTCOME

After completion:
- ✅ Full enterprise UI with sidebar, message list, input bar
- ✅ Thinking blocks show/hide reasoning
- ✅ Conversations persist in sidebar
- ✅ Branded as "AetherAI powered by Apriel"
- ✅ Streaming works perfectly
- ✅ Mobile responsive
- ✅ TypeScript errors gone
- ✅ Production-ready for aetherpro.tech

---

**Claude Code: Execute this plan in order. Report any errors immediately. Test after Phase 7 before deploying.**

## Additional Notes: I have added a logo & favicon images, you will find them in public directory.

 
**File locations:**
```
/public/
  ├── logo.svg          # Vector version (get this from AI or recreate)
  ├── logo.png          # 1024x1024 for general use
  ├── logo-sm.png       # 256x256 for favicons
  └── favicon.ico       # Generated from logo-sm.png
```

**Component usage:**
```typescript
// In Logo.tsx component
<img src="/logo.png" alt="AetherAI" className="w-12 h-12" />

// Or inline SVG for better control
<svg viewBox="0 0 100 100" className="w-12 h-12">
  {/* Y-node paths */}
</svg>
```

--
