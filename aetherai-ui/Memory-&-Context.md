Short version:

* Saving convo = frontend state + localStorage.
* Controlling context = *you* decide which slice of that history you send to vLLM.
  Right now you’re probably sending everything, so Apriel keeps “remembering.”

Let’s split the two concerns cleanly.

---

## 1. Save conversations **only in the frontend**

Assume React/Next, single chat window.

### a) Message shape

```ts
export type ChatRole = 'system' | 'user' | 'assistant' | 'tool';

export interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  createdAt: string;
}

export interface ChatSession {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  messages: ChatMessage[];
}
```

### b) Local storage helpers

```ts
const STORAGE_KEY = 'aether_chat_sessions_v1';

function loadSessions(): ChatSession[] {
  if (typeof window === 'undefined') return [];
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    return JSON.parse(raw);
  } catch {
    return [];
  }
}

function saveSessions(sessions: ChatSession[]) {
  if (typeof window === 'undefined') return;
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions));
}
```

### c) Hook to manage sessions

```ts
import { useEffect, useState } from 'react';
import { nanoid } from 'nanoid';

export function useChatSessions() {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);

  // Load from localStorage on mount
  useEffect(() => {
    const loaded = loadSessions();
    setSessions(loaded);
    if (loaded.length && !activeId) {
      setActiveId(loaded[0].id);
    }
  }, []);

  // Persist whenever sessions change
  useEffect(() => {
    if (sessions.length) saveSessions(sessions);
  }, [sessions]);

  const createSession = (title: string): ChatSession => {
    const now = new Date().toISOString();
    const session: ChatSession = {
      id: nanoid(),
      title,
      createdAt: now,
      updatedAt: now,
      messages: [],
    };
    setSessions(prev => [session, ...prev]);
    setActiveId(session.id);
    return session;
  };

  const updateSession = (id: string, updater: (s: ChatSession) => ChatSession) => {
    setSessions(prev =>
      prev.map(s => (s.id === id ? updater(s) : s)),
    );
  };

  const appendMessage = (id: string, msg: Omit<ChatMessage, 'id' | 'createdAt'>) => {
    const now = new Date().toISOString();
    updateSession(id, s => ({
      ...s,
      updatedAt: now,
      messages: [...s.messages, { ...msg, id: nanoid(), createdAt: now }],
    }));
  };

  const activeSession = sessions.find(s => s.id === activeId) ?? null;

  return {
    sessions,
    activeSession,
    activeId,
    setActiveId,
    createSession,
    appendMessage,
  };
}
```

That gets you:

* Multiple saved conversations.
* All frontend only.
* Survives refresh, no backend DB needed.

Plug that into your chat component and use `appendMessage` whenever user or Apriel speaks.

---

## 2. Control **context** separately from saved history

Key rule: **UI history ≠ model context**.

You can save the *entire* chat in the frontend, but only feed part of it into your vLLM router.

You’re probably doing something like:

```ts
await fetch('/api/chat', {
  method: 'POST',
  body: JSON.stringify({ messages: session.messages }),
});
```

…which means Apriel sees every message since the beginning of time. That’s why she’s referencing old prompts.

### a) Sliding window: only send last N turns

Define a selector:

```ts
const MAX_CONTEXT_TURNS = 6; // last 6 user messages (and their replies)

function buildContext(messages: ChatMessage[]) {
  // Keep only user/assistant messages for context
  const core = messages.filter(m =>
    m.role === 'user' || m.role === 'assistant',
  );

  const tail = core.slice(-MAX_CONTEXT_TURNS * 2); // user+assistant pairs

  const system: ChatMessage = {
    id: 'system',
    role: 'system',
    content: 'You are Apriel, running inside AetherPro. Answer clearly and concisely.',
    createdAt: new Date().toISOString(),
  };

  return [system, ...tail];
}
```

Then when you call your 3-pass router:

```ts
const contextMessages = buildContext(activeSession.messages);

await fetch('/api/router', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    messages: contextMessages,
    // pass whatever you need: passType: 'tool_select' | 'tool_call' | 'final'
  }),
});
```

Apriel will:

* Still *show* full history in the UI.
* Only *see* the last `MAX_CONTEXT_TURNS` turns for reasoning.

You can adjust `MAX_CONTEXT_TURNS` or use token counts later, but this is the simple, effective version.

---

### b) “Hard reset” button without killing the saved convo

Sometimes you want to:

* Keep the conversation in UI for reference,
* But tell the model “start fresh now.”

Simplest trick: track an index where context starts.

```ts
export interface ChatSession {
  // ...
  contextStartIndex?: number; // default 0
}
```

When user clicks “Reset Context”:

```ts
const resetContext = (sessionId: string) => {
  updateSession(sessionId, s => ({
    ...s,
    contextStartIndex: s.messages.length, // future messages only
  }));
};
```

Then modify `buildContext`:

```ts
function buildContext(session: ChatSession) {
  const start = session.contextStartIndex ?? 0;
  const slice = session.messages.slice(start);

  const core = slice.filter(
    m => m.role === 'user' || m.role === 'assistant',
  );
  const tail = core.slice(-MAX_CONTEXT_TURNS * 2);

  const system: ChatMessage = {
    id: 'system',
    role: 'system',
    content: 'You are Apriel… (whatever priming)',
    createdAt: new Date().toISOString(),
  };

  return [system, ...tail];
}
```

Now you’ve got:

* A running conversation in the UI (scroll back forever).
* A controllable context window the model sees.
* A one-click “new thread from here” behavior without creating a brand-new session.

---

### c) Where the 3-pass router fits

You already have:

1. Pass 1: decide tools.
2. Pass 2: emit tool calls.
3. Pass 3: final merged answer.

Context handling is the same for all passes:

* For each pass, you send `buildContext(session)` to the backend.
* The backend/router stays stateless (no DB memory required).
* Tool results get appended to `session.messages` on frontend (or backend then echoed), and the *next* pass just uses the updated `buildContext`.

If you’re currently storing history server-side, you can still move to **frontend-authoritative**:

* Frontend sends full `messages` (for persistence),
* Router uses `buildContext(messages)` internally before forwarding to vLLM.

But if you want “frontend only,” easiest is: backend does **no** long-term storage; just trusts whatever `messages` array the client sends.

---

Bottom line:

* You already have the hard part (vLLM + router on L40S).
* “Conversation saving” is just React state + localStorage.
* “Context control” is literally one function deciding which slice of `messages` the router sees.

Once that’s in place, you can start doing fancier stuff like “summarize previous 50 messages down to a memory chunk,” but this gives you clean control *today* without breaking Apriel’s brain.
