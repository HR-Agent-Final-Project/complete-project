import React, { useState, useRef, useEffect } from 'react';
import { Bot, X, Send, Minimize2 } from 'lucide-react';
import { ChatMessage } from '../../types';
import { chatApi } from '../../services/api';
import { useNavigate } from 'react-router-dom';

const QUICK_PROMPTS = [
  'Check my leave balance',
  'Apply for leave tomorrow',
  'What\'s the attendance policy?',
];

export const ChatWidget = () => {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([
    { id: 'init', role: 'assistant', content: 'Hi! I\'m HRAgent AI. How can I help you today?', timestamp: new Date().toISOString() },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [convId, setConvId] = useState<string | undefined>();
  const bottomRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const send = async (text: string) => {
    if (!text.trim() || loading) return;
    const userMsg: ChatMessage = { id: `u-${Date.now()}`, role: 'user', content: text, timestamp: new Date().toISOString() };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);
    try {
      const res = await chatApi.sendMessage(text, convId);
      setConvId(res.conversation_id);
      setMessages(prev => [...prev, {
        id: `a-${Date.now()}`, role: 'assistant', content: res.response, timestamp: new Date().toISOString(),
      }]);
    } catch {
      setMessages(prev => [...prev, {
        id: `err-${Date.now()}`, role: 'assistant', content: 'Sorry, I encountered an error. Please try again.', timestamp: new Date().toISOString(),
      }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      {/* FAB */}
      <button
        onClick={() => setOpen(true)}
        className={`fixed bottom-6 right-6 z-40 w-14 h-14 bg-neo-teal border-4 border-neo-black shadow-neo-lg flex items-center justify-center hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-neo transition-all ${open ? 'hidden' : ''}`}
        title="Open AI Chat"
      >
        <Bot size={24} className="text-neo-black" />
      </button>

      {/* Chat Modal */}
      {open && (
        <div className="fixed bottom-6 right-6 z-50 w-80 flex flex-col border-2 border-neo-black shadow-neo-lg bg-white"
          style={{ height: '420px' }}>
          {/* Header */}
          <div className="bg-neo-teal border-b-2 border-neo-black px-3 py-2 flex items-center justify-between flex-shrink-0">
            <div className="flex items-center gap-2">
              <Bot size={16} className="text-neo-black" />
              <span className="font-display font-bold text-sm text-neo-black">HRAgent AI</span>
              <span className="w-2 h-2 bg-green-500 border border-neo-black rounded-full" />
            </div>
            <div className="flex items-center gap-1">
              <button
                onClick={() => { setOpen(false); navigate('/ai-chat'); }}
                className="p-1 border-2 border-neo-black bg-white hover:bg-neo-yellow transition-colors"
                title="Open full chat"
              ><Minimize2 size={12} /></button>
              <button onClick={() => setOpen(false)} className="p-1 border-2 border-neo-black bg-white hover:bg-neo-coral transition-colors">
                <X size={12} />
              </button>
            </div>
          </div>

          {/* Quick prompts */}
          <div className="flex gap-1 p-2 border-b-2 border-neo-black flex-shrink-0 flex-wrap">
            {QUICK_PROMPTS.map(p => (
              <button key={p} onClick={() => send(p)}
                className="text-[10px] font-mono border border-neo-black px-1.5 py-0.5 bg-neo-yellow hover:bg-neo-teal transition-colors">
                {p}
              </button>
            ))}
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-2 flex flex-col gap-2">
            {messages.map(m => (
              <div key={m.id} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[85%] border-2 border-neo-black px-2.5 py-1.5 text-xs font-mono ${m.role === 'user' ? 'bg-neo-yellow' : 'bg-white'}`}>
                  {m.content}
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex justify-start">
                <div className="border-2 border-neo-black px-3 py-2 bg-white flex gap-1 items-center">
                  <span className="typing-dot w-1.5 h-1.5 bg-neo-black rounded-full" />
                  <span className="typing-dot w-1.5 h-1.5 bg-neo-black rounded-full" />
                  <span className="typing-dot w-1.5 h-1.5 bg-neo-black rounded-full" />
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          {/* Input */}
          <div className="border-t-2 border-neo-black flex flex-shrink-0">
            <input
              className="flex-1 px-3 py-2 text-xs font-mono border-none outline-none bg-white"
              placeholder="Ask anything HR..."
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && send(input)}
            />
            <button
              onClick={() => send(input)}
              disabled={!input.trim() || loading}
              className="px-3 bg-neo-teal border-l-2 border-neo-black hover:bg-neo-yellow disabled:opacity-50 transition-colors"
            >
              <Send size={14} />
            </button>
          </div>
        </div>
      )}
    </>
  );
};
