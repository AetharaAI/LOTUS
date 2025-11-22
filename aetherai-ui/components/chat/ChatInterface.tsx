'use client';

import React, { useState, useRef, useEffect } from 'react';
import Draggable from 'react-draggable';
import { Terminal, Activity, Minimize2, Maximize2, Send, Cpu, Zap } from 'lucide-react';
import { streamChat } from '@/lib/api/streaming';

// --- TYPE DEFINITION (Fixed locally so build passes) ---
type Message = {
  role: string;
  content: string;
};

export default function ChatInterface() {
  // -- STATE --
  const [isExpanded, setIsExpanded] = useState(true);
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  
  // -- THE DISPLAY BUFFERS --
  const [thinkingBuffer, setThinkingBuffer] = useState('');
  const [contentBuffer, setContentBuffer] = useState('');
  const [conversation, setConversation] = useState<Message[]>([]);

  // -- REFS FOR AUTO-SCROLL --
  const thinkRef = useRef<HTMLDivElement>(null);
  const contentRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (thinkRef.current) thinkRef.current.scrollTop = thinkRef.current.scrollHeight;
    if (contentRef.current) contentRef.current.scrollTop = contentRef.current.scrollHeight;
  }, [thinkingBuffer, contentBuffer]);

  // -- HANDLER --
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isStreaming) return;

    const userMsg = input;
    setInput('');
    setIsStreaming(true);
    setThinkingBuffer(''); // Reset voltage
    setContentBuffer('');  // Reset amps

    // Add user message to history immediately
    const newHistory = [...conversation, { role: 'user', content: userMsg }];
    setConversation(newHistory);

    try {
      await streamChat(
        {
          messages: newHistory,
          model: 'apriel-1.5-15b-thinker',
          temperature: 0.3
        },
        {
          // ROUTE 1: THE THINKING MONITOR
          onThinking: (chunk) => {
            setThinkingBuffer(prev => prev + chunk);
          },
          
          // ROUTE 2: THE FINAL OUTPUT
          onContent: (chunk) => {
            setContentBuffer(prev => prev + chunk);
          },

          onDone: () => {
            setIsStreaming(false);
            // Commit the transaction to history
            setConversation(prev => [...prev, { role: 'assistant', content: contentBuffer }]);
          },
          
          onError: (err) => {
            console.error("Breaker Tripped:", err);
            setIsStreaming(false);
          }
        }
      );
    } catch (error) {
      setIsStreaming(false);
    }
  };

  return (
    <div className="fixed inset-0 pointer-events-none z-50 overflow-hidden">
      {/* POINTER EVENTS AUTO allows clicking the widget, but passing clicks through the empty space */}
      <Draggable handle=".drag-handle" bounds="parent">
        <div className="pointer-events-auto absolute bottom-10 right-10 w-[500px] flex flex-col shadow-2xl shadow-black/50 rounded-lg border border-slate-700 bg-slate-950 text-slate-200 overflow-hidden">
          
          {/* --- HEADER (DRAG HANDLE) --- */}
          <div className="drag-handle h-10 bg-slate-900 border-b border-slate-800 flex items-center justify-between px-4 cursor-move select-none">
            <div className="flex items-center gap-2 text-blue-400">
              <Activity size={16} className={isStreaming ? "animate-pulse text-green-400" : ""} />
              <span className="font-mono text-xs font-bold tracking-widest">APRIEL // L40S-NODE</span>
            </div>
            <div className="flex items-center gap-2">
                {/* Status Lights */}
                <div className={`w-2 h-2 rounded-full ${isStreaming ? 'bg-green-500' : 'bg-slate-600'}`} />
                <button onClick={() => setIsExpanded(!isExpanded)} className="hover:text-white ml-2">
                {isExpanded ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
                </button>
            </div>
          </div>

          {/* --- EXPANDED VIEW --- */}
          {isExpanded && (
            <div className="flex flex-col h-[600px]">
              
              {/* ZONE 1: THE THINKING MONITOR (High Voltage) */}
              <div className="h-1/3 bg-slate-950 border-b border-slate-800 p-3 overflow-y-auto font-mono text-xs text-amber-500/80" ref={thinkRef}>
                <div className="flex items-center gap-2 text-slate-500 mb-2 sticky top-0 bg-slate-950/90 backdrop-blur">
                    <Cpu size={12} />
                    <span className="uppercase tracking-wider">Internal Logic Chain</span>
                </div>
                {thinkingBuffer ? (
                    <pre className="whitespace-pre-wrap font-mono">{thinkingBuffer}</pre>
                ) : (
                    <span className="text-slate-700 italic">Waiting for reasoning stream...</span>
                )}
              </div>

              {/* ZONE 2: THE OUTPUT MONITOR (Amperage) */}
              <div className="flex-1 bg-slate-900/50 p-4 overflow-y-auto scrollbar-thin" ref={contentRef}>
                {conversation.map((msg, i) => (
                    <div key={i} className={`mb-4 ${msg.role === 'user' ? 'text-right' : 'text-left'}`}>
                        <div className={`inline-block p-2 rounded ${msg.role === 'user' ? 'bg-blue-900/30 text-blue-100 border border-blue-800' : 'text-slate-200'}`}>
                            {msg.content}
                        </div>
                    </div>
                ))}
                
                {/* Live Streaming Content */}
                {contentBuffer && (
                    <div className="text-left">
                        <div className="inline-block text-slate-200 animate-pulse-fast">
                            {contentBuffer}
                            <span className="inline-block w-2 h-4 bg-blue-500 ml-1 align-middle animate-pulse"/>
                        </div>
                    </div>
                )}
              </div>

              {/* ZONE 3: INPUT TERMINAL */}
              <form onSubmit={handleSubmit} className="h-14 bg-slate-950 border-t border-slate-800 flex items-center px-3 gap-2">
                <Terminal size={16} className="text-blue-500" />
                <input 
                    className="flex-1 bg-transparent border-none focus:ring-0 text-sm font-mono text-white placeholder-slate-600"
                    placeholder="Enter command sequence..."
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    autoFocus
                />
                <button type="submit" disabled={isStreaming} className="text-slate-400 hover:text-blue-400 disabled:opacity-30">
                    <Zap size={18} />
                </button>
              </form>

            </div>
          )}
        </div>
      </Draggable>
    </div>
  );
}