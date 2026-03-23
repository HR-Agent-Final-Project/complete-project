import React, { useState, useRef, useEffect, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import { Send, Plus, Bot, User, Trash2, FileText, PanelLeftOpen, PanelLeftClose, Sparkles, MessageSquare, Zap, Mic, Volume2, VolumeX, Square, CircleStop } from 'lucide-react';
import { ChatMessage, Conversation } from '../types';
import { chatApi } from '../services/api';
import { NeoCard } from '../components/ui/NeoCard';
import { NeoButton } from '../components/ui/NeoButton';
import axios from 'axios';

const QUICK_PROMPTS = [
  { text: 'Check my leave balance', icon: '\u{1F4CB}' },
  { text: 'Apply for leave tomorrow', icon: '\u{1F3D6}\u{FE0F}' },
  { text: "What's the attendance policy?", icon: '\u{1F4D6}' },
  { text: 'Show my performance summary', icon: '\u{1F4CA}' },
  { text: 'What are company working hours?', icon: '\u{1F550}' },
  { text: 'How to request overtime?', icon: '\u{23F0}' },
];

const WELCOME_MESSAGE: ChatMessage = {
  id: 'init',
  role: 'assistant',
  content:
    "Hello! I'm HRAgent AI, your intelligent HR assistant. I can help you with leave requests, attendance queries, company policies, and much more. What can I help you with today?",
  timestamp: new Date().toISOString(),
};

/* ── Decorative shapes ────────────────────────────────────────── */
const DecoCircle = ({ size, color, className }: { size: number; color: string; className?: string }) => (
  <div
    className={`absolute rounded-full border-[3px] border-neo-black shadow-neo-sm pointer-events-none ${className}`}
    style={{ width: size, height: size, backgroundColor: color }}
  />
);

const DecoSquare = ({ size, color, className, rotate = 0 }: { size: number; color: string; className?: string; rotate?: number }) => (
  <div
    className={`absolute border-[3px] border-neo-black shadow-neo-sm pointer-events-none ${className}`}
    style={{ width: size, height: size, backgroundColor: color, transform: `rotate(${rotate}deg)` }}
  />
);

/* ── Markdown Renderer ────────────────────────────────────────── */
const MarkdownContent = ({ children }: { children: string }) => (
  <ReactMarkdown
    components={{
      p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
      strong: ({ children }) => <strong className="font-bold text-neo-black">{children}</strong>,
      em: ({ children }) => <em className="italic">{children}</em>,
      ul: ({ children }) => <ul className="list-disc list-inside mb-2 space-y-1">{children}</ul>,
      ol: ({ children }) => <ol className="list-decimal list-inside mb-2 space-y-1">{children}</ol>,
      li: ({ children }) => <li className="ml-2">{children}</li>,
      code: ({ children }) => <code className="bg-neo-bg border border-neo-black/20 px-1 py-0.5 text-[11px] rounded">{children}</code>,
      h1: ({ children }) => <h1 className="font-display font-bold text-base mb-1">{children}</h1>,
      h2: ({ children }) => <h2 className="font-display font-bold text-sm mb-1">{children}</h2>,
      h3: ({ children }) => <h3 className="font-display font-bold text-xs mb-1">{children}</h3>,
    }}
  >
    {children}
  </ReactMarkdown>
);

/* ── Typewriter Text Component ────────────────────────────────── */
const TypewriterText = ({ text, onComplete, speed = 18 }: { text: string; onComplete?: () => void; speed?: number }) => {
  const [displayed, setDisplayed] = useState('');
  const [done, setDone] = useState(false);
  const indexRef = useRef(0);
  const timerRef = useRef<ReturnType<typeof setTimeout>>();

  useEffect(() => {
    indexRef.current = 0;
    setDisplayed('');
    setDone(false);

    const tick = () => {
      indexRef.current++;
      const next = text.slice(0, indexRef.current);
      setDisplayed(next);

      if (indexRef.current >= text.length) {
        setDone(true);
        onComplete?.();
      } else {
        // Variable speed: pause longer after punctuation
        const char = text[indexRef.current - 1];
        const delay = '.!?\n'.includes(char) ? speed * 6 : char === ',' ? speed * 3 : speed;
        timerRef.current = setTimeout(tick, delay);
      }
    };
    timerRef.current = setTimeout(tick, speed);

    return () => { if (timerRef.current) clearTimeout(timerRef.current); };
  }, [text, speed, onComplete]);

  if (done) return <MarkdownContent>{text}</MarkdownContent>;

  return (
    <span>
      {displayed}
      <span className="inline-block w-[2px] h-[1em] bg-neo-black ml-0.5 align-text-bottom animate-pulse" />
    </span>
  );
};

/* ── Voice Waveform Visualizer ────────────────────────────────── */
const VoiceWaveform = ({ isRecording, analyser }: { isRecording: boolean; analyser: AnalyserNode | null }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animRef = useRef<number>(0);

  useEffect(() => {
    if (!isRecording || !analyser || !canvasRef.current) return;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);

    const draw = () => {
      animRef.current = requestAnimationFrame(draw);
      analyser.getByteTimeDomainData(dataArray);

      ctx.fillStyle = '#FFFBF0';
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      ctx.lineWidth = 3;
      ctx.strokeStyle = '#0A0A0A';
      ctx.beginPath();

      const sliceWidth = canvas.width / bufferLength;
      let x = 0;
      for (let i = 0; i < bufferLength; i++) {
        const v = dataArray[i] / 128.0;
        const y = (v * canvas.height) / 2;
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
        x += sliceWidth;
      }
      ctx.lineTo(canvas.width, canvas.height / 2);
      ctx.stroke();

      ctx.fillStyle = '#00C9B1';
      for (let i = 0; i < bufferLength; i += Math.floor(bufferLength / 8)) {
        const v = dataArray[i] / 128.0;
        const y = (v * canvas.height) / 2;
        const dotX = (i / bufferLength) * canvas.width;
        if (Math.abs(v - 1) > 0.1) {
          ctx.beginPath();
          ctx.arc(dotX, y, 4, 0, Math.PI * 2);
          ctx.fill();
        }
      }
    };
    draw();
    return () => cancelAnimationFrame(animRef.current);
  }, [isRecording, analyser]);

  if (!isRecording) return null;

  return (
    <div className="border-2 border-neo-black bg-neo-bg shadow-neo-sm p-2">
      <canvas ref={canvasRef} width={320} height={60} className="w-full h-[60px]" />
    </div>
  );
};

/* ── Pulsing Recording Indicator ──────────────────────────────── */
const PulseRing = () => (
  <>
    <span className="absolute inset-0 rounded-full bg-neo-coral/30 animate-ping" />
    <span className="absolute -inset-1 rounded-full border-2 border-neo-coral/40 animate-pulse" />
  </>
);

export const AIChat = () => {
  const [conversations, setConversations]     = useState<Conversation[]>([]);
  const [activeConvId, setActiveConvId]       = useState<string | null>(null);
  const [messages, setMessages]               = useState<ChatMessage[]>([WELCOME_MESSAGE]);
  const [input, setInput]                     = useState('');
  const [loading, setLoading]                 = useState(false);
  const [historyLoading, setHistoryLoading]   = useState(false);
  const [sessionId, setSessionId]             = useState<string | undefined>();
  const [sources, setSources]                 = useState<string[]>([]);
  const [historyPanelOpen, setHistoryPanelOpen] = useState(false);
  const bottomRef  = useRef<HTMLDivElement>(null);
  const inputRef   = useRef<HTMLInputElement>(null);

  // ── Voice state ──
  const [isRecording, setIsRecording]     = useState(false);
  const [voiceLoading, setVoiceLoading]   = useState(false);
  const [voiceMode, setVoiceMode]         = useState(false);
  const [analyser, setAnalyser]           = useState<AnalyserNode | null>(null);
  const [isPlaying, setIsPlaying]         = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef   = useRef<Blob[]>([]);
  const audioContextRef  = useRef<AudioContext | null>(null);
  const currentAudioRef  = useRef<HTMLAudioElement | null>(null);

  // ── Typewriter state ──
  const [typingMsgId, setTypingMsgId] = useState<string | null>(null);

  // ── Abort controller for cancelling requests ──
  const abortControllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    chatApi.getConversations().then(setConversations).catch(() => {});
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading, voiceLoading, typingMsgId]);

  // ── Stop / cancel AI response ──
  const stopResponse = useCallback(() => {
    // Cancel any in-flight HTTP request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }

    // Stop TTS audio
    if (currentAudioRef.current) {
      currentAudioRef.current.pause();
      currentAudioRef.current.currentTime = 0;
      setIsPlaying(false);
    }

    // If typewriter is running, skip to full text (already in messages)
    if (typingMsgId) {
      setTypingMsgId(null);
    }

    setLoading(false);
    setVoiceLoading(false);
  }, [typingMsgId]);

  // ── Text send ──
  const send = async (text: string) => {
    if (!text.trim() || loading) return;

    const userMsg: ChatMessage = {
      id: `u-${Date.now()}`,
      role: 'user',
      content: text,
      timestamp: new Date().toISOString(),
    };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setSources([]);
    setLoading(true);

    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      const res = await chatApi.sendMessage(text, sessionId);

      // If aborted, don't process
      if (controller.signal.aborted) return;

      setSessionId(res.conversation_id);
      setSources(res.sources || []);

      const aiMsgId = `a-${Date.now()}`;
      setMessages(prev => [
        ...prev,
        {
          id: aiMsgId,
          role: 'assistant',
          content: res.response,
          timestamp: new Date().toISOString(),
        },
      ]);
      // Start typewriter on this message
      setTypingMsgId(aiMsgId);

      chatApi.getConversations().then(setConversations).catch(() => {});
    } catch (err) {
      if (axios.isCancel(err) || controller.signal.aborted) {
        // User stopped — add a note
        setMessages(prev => [
          ...prev,
          {
            id: `stopped-${Date.now()}`,
            role: 'assistant',
            content: '[Response stopped]',
            timestamp: new Date().toISOString(),
          },
        ]);
      } else {
        setMessages(prev => [
          ...prev,
          {
            id: `err-${Date.now()}`,
            role: 'assistant',
            content: 'I apologize, I encountered an error. Please try again.',
            timestamp: new Date().toISOString(),
          },
        ]);
      }
    } finally {
      setLoading(false);
      abortControllerRef.current = null;
    }
  };

  // ── Voice recording ──
  const startRecording = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const audioCtx = new AudioContext();
      audioContextRef.current = audioCtx;
      const source = audioCtx.createMediaStreamSource(stream);
      const analyserNode = audioCtx.createAnalyser();
      analyserNode.fftSize = 2048;
      source.connect(analyserNode);
      setAnalyser(analyserNode);

      const mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm;codecs=opus' });
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunksRef.current.push(e.data);
      };

      mediaRecorder.onstop = async () => {
        stream.getTracks().forEach(t => t.stop());
        audioCtx.close();
        setAnalyser(null);

        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        if (audioBlob.size < 100) return;

        const listeningMsg: ChatMessage = {
          id: `vu-${Date.now()}`,
          role: 'user',
          content: '\u{1F3A4} Voice message...',
          timestamp: new Date().toISOString(),
        };
        setMessages(prev => [...prev, listeningMsg]);
        setVoiceLoading(true);
        setSources([]);

        const controller = new AbortController();
        abortControllerRef.current = controller;

        try {
          const res = await chatApi.sendVoice(audioBlob, sessionId);

          if (controller.signal.aborted) return;

          setSessionId(res.session_id);
          setSources(res.sources || []);

          const aiMsgId = `va-${Date.now()}`;
          setMessages(prev => {
            const updated = prev.map(m =>
              m.id === listeningMsg.id
                ? { ...m, content: res.transcript }
                : m
            );
            return [
              ...updated,
              {
                id: aiMsgId,
                role: 'assistant' as const,
                content: res.response,
                timestamp: new Date().toISOString(),
              },
            ];
          });

          // Start typewriter on AI response
          setTypingMsgId(aiMsgId);

          // Play TTS audio
          if (res.audio_base64) {
            playAudio(res.audio_base64);
          }

          chatApi.getConversations().then(setConversations).catch(() => {});
        } catch (err) {
          if (axios.isCancel(err) || controller.signal.aborted) {
            setMessages(prev => [
              ...prev.filter(m => m.id !== listeningMsg.id),
              {
                id: `stopped-${Date.now()}`,
                role: 'assistant',
                content: '[Response stopped]',
                timestamp: new Date().toISOString(),
              },
            ]);
          } else {
            setMessages(prev => [
              ...prev.filter(m => m.id !== listeningMsg.id),
              {
                id: `verr-${Date.now()}`,
                role: 'assistant',
                content: 'Voice processing failed. Please try again or type your message.',
                timestamp: new Date().toISOString(),
              },
            ]);
          }
        } finally {
          setVoiceLoading(false);
          abortControllerRef.current = null;
        }
      };

      mediaRecorder.start();
      setIsRecording(true);
    } catch {
      alert('Microphone access denied. Please allow microphone access in your browser settings.');
    }
  }, [sessionId]);

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  }, [isRecording]);

  const playAudio = (base64: string) => {
    if (currentAudioRef.current) {
      currentAudioRef.current.pause();
    }
    const audio = new Audio(`data:audio/mp3;base64,${base64}`);
    currentAudioRef.current = audio;
    setIsPlaying(true);
    audio.onended = () => setIsPlaying(false);
    audio.onerror = () => setIsPlaying(false);
    audio.play();
  };

  const stopAudio = () => {
    if (currentAudioRef.current) {
      currentAudioRef.current.pause();
      currentAudioRef.current.currentTime = 0;
      setIsPlaying(false);
    }
  };

  const newConversation = () => {
    stopResponse();
    setMessages([
      {
        id: 'init-' + Date.now(),
        role: 'assistant',
        content: 'New conversation started. How can I help you?',
        timestamp: new Date().toISOString(),
      },
    ]);
    setSessionId(undefined);
    setActiveConvId(null);
    setSources([]);
    setTypingMsgId(null);
  };

  const loadConversation = async (conv: Conversation) => {
    if (activeConvId === conv.id) return;
    stopResponse();
    setActiveConvId(conv.id);
    setSessionId(conv.id);
    setSources([]);
    setHistoryLoading(true);
    setTypingMsgId(null);
    try {
      const session = await chatApi.getSession(conv.id);
      setMessages(
        session.messages.length > 0
          ? session.messages
          : [{ id: 'empty', role: 'assistant', content: 'No messages in this session yet.', timestamp: new Date().toISOString() }],
      );
    } catch {
      setMessages([{ id: 'err', role: 'assistant', content: 'Could not load this conversation.', timestamp: new Date().toISOString() }]);
    } finally {
      setHistoryLoading(false);
    }
  };

  const deleteConversation = async (conv: Conversation, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await chatApi.deleteSession(conv.id);
      setConversations(prev => prev.filter(c => c.id !== conv.id));
      if (activeConvId === conv.id) newConversation();
    } catch {}
  };

  const formatTime = (ts: string) =>
    new Date(ts).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });

  const isFirstMessage = messages.length === 1 && messages[0].id.startsWith('init');
  const isBusy = loading || voiceLoading || historyLoading;
  const canStop = loading || voiceLoading || isPlaying || typingMsgId !== null;

  return (
    <div className="flex h-[calc(100dvh-4rem)] md:h-[calc(100vh-5rem)] gap-3 md:gap-4 relative">
      {/* ── History Panel ── */}
      {historyPanelOpen && (
        <div className="fixed inset-0 bg-black/40 z-30 md:hidden" onClick={() => setHistoryPanelOpen(false)} />
      )}
      <div className={`
        absolute md:static inset-y-0 left-0 z-40
        w-64 flex-shrink-0 flex flex-col gap-3
        transition-transform duration-200
        ${historyPanelOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}
      `}>
        <NeoButton variant="teal" icon={<Plus size={16} />} onClick={newConversation} className="w-full">
          New Chat
        </NeoButton>

        <NeoCard padding="p-0" className="flex-1 overflow-hidden flex flex-col">
          <div className="bg-neo-bg px-4 py-3 border-b-2 border-neo-black">
            <p className="font-display font-bold text-xs uppercase tracking-widest flex items-center gap-2">
              <MessageSquare size={12} />
              Chat History
            </p>
          </div>
          <div className="flex-1 overflow-y-auto p-2">
            {conversations.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-8 px-4 text-center">
                <div className="w-12 h-12 bg-neo-bg border-2 border-neo-black shadow-neo-sm flex items-center justify-center mb-3 rounded-full">
                  <MessageSquare size={18} className="text-gray-400" />
                </div>
                <p className="font-mono text-xs text-gray-400">No conversations yet</p>
                <p className="font-mono text-[10px] text-gray-300 mt-1">Start chatting to see history</p>
              </div>
            ) : (
              conversations.map(conv => (
                <div
                  key={conv.id}
                  onClick={() => loadConversation(conv)}
                  className={`group flex items-start gap-2 p-2.5 border-2 mb-1.5 cursor-pointer transition-all
                    ${activeConvId === conv.id
                      ? 'border-neo-black bg-neo-yellow shadow-neo-sm'
                      : 'border-transparent hover:border-neo-black hover:bg-neo-yellow/20'}`}
                >
                  <div className={`w-6 h-6 border-2 border-neo-black flex items-center justify-center flex-shrink-0 mt-0.5
                    ${activeConvId === conv.id ? 'bg-neo-black' : 'bg-neo-bg'}`}>
                    <MessageSquare size={10} className={activeConvId === conv.id ? 'text-neo-yellow' : 'text-gray-500'} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="font-display font-bold text-xs text-neo-black truncate">{conv.title}</p>
                    <p className="font-mono text-[10px] text-gray-500 truncate mt-0.5">{conv.last_message}</p>
                  </div>
                  <button
                    onClick={e => deleteConversation(conv, e)}
                    className="opacity-0 group-hover:opacity-100 p-1 hover:bg-neo-coral hover:text-white border-2 border-transparent hover:border-neo-black transition-all flex-shrink-0"
                    title="Delete session"
                  >
                    <Trash2 size={10} />
                  </button>
                </div>
              ))
            )}
          </div>
        </NeoCard>
      </div>

      {/* ── Main Chat ── */}
      <div className="flex-1 flex flex-col border-2 border-neo-black shadow-neo-lg bg-white min-w-0 overflow-hidden">
        {/* Header */}
        <div className="bg-neo-yellow border-b-2 border-neo-black px-4 md:px-5 py-3 flex items-center justify-between flex-shrink-0">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setHistoryPanelOpen(o => !o)}
              className="md:hidden p-1.5 border-2 border-neo-black bg-white hover:bg-white/70 transition-colors flex-shrink-0"
              title="Toggle history"
            >
              {historyPanelOpen ? <PanelLeftClose size={14} /> : <PanelLeftOpen size={14} />}
            </button>
            <div className="relative">
              <div className="w-10 h-10 bg-neo-black border-2 border-neo-black flex items-center justify-center rounded-full">
                <Bot size={20} className="text-neo-yellow" />
              </div>
              <div className="absolute -bottom-0.5 -right-0.5 w-3.5 h-3.5 bg-neo-teal rounded-full border-2 border-neo-black" />
            </div>
            <div>
              <p className="font-display font-bold text-sm flex items-center gap-1.5">
                HRAgent AI
                <span className="inline-flex items-center gap-1 bg-neo-black text-neo-yellow text-[9px] font-mono px-1.5 py-0.5 uppercase tracking-wider">
                  <Zap size={8} /> Pro
                </span>
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {/* Voice mode toggle */}
            <button
              onClick={() => { setVoiceMode(v => !v); stopAudio(); }}
              className={`p-2 border-2 border-neo-black transition-all shadow-neo-sm hover:shadow-none hover:translate-x-[2px] hover:translate-y-[2px]
                ${voiceMode ? 'bg-neo-teal text-neo-black' : 'bg-white hover:bg-neo-teal'}`}
              title={voiceMode ? 'Switch to text mode' : 'Switch to voice mode'}
            >
              <Mic size={14} />
            </button>
            <button
              onClick={newConversation}
              className="p-2 border-2 border-neo-black bg-white hover:bg-neo-coral hover:text-white transition-colors shadow-neo-sm hover:shadow-none hover:translate-x-[2px] hover:translate-y-[2px]"
              title="New conversation"
            >
              <Plus size={14} />
            </button>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto relative">
          {/* Background decorative shapes */}
          <div className="absolute inset-0 overflow-hidden pointer-events-none opacity-[0.07]">
            <DecoCircle size={120} color="#FFE135" className="-top-8 -right-8" />
            <DecoCircle size={80} color="#00C9B1" className="top-1/4 -left-6" />
            <DecoSquare size={60} color="#FF6B6B" className="top-1/3 right-12" rotate={15} />
            <DecoCircle size={50} color="#4D96FF" className="bottom-1/4 -right-4" />
            <DecoSquare size={40} color="#FFE135" className="bottom-1/3 left-8" rotate={-12} />
            <DecoCircle size={90} color="#FF6B6B" className="-bottom-6 right-1/4" />
            <DecoSquare size={35} color="#00C9B1" className="top-16 left-1/3" rotate={45} />
          </div>

          <div className="relative z-10 p-4 md:p-6 flex flex-col gap-5">
            {historyLoading ? (
              <div className="flex-1 flex items-center justify-center py-20">
                <div className="flex flex-col items-center gap-4">
                  <div className="w-14 h-14 bg-neo-yellow border-2 border-neo-black shadow-neo flex items-center justify-center rounded-full animate-pulse">
                    <Bot size={24} className="text-neo-black" />
                  </div>
                  <p className="font-mono text-sm text-gray-400">Loading conversation...</p>
                </div>
              </div>
            ) : (
              <>
                {/* Welcome hero */}
                {isFirstMessage && (
                  <div className="flex flex-col items-center text-center py-6 mb-2">
                    <div className="relative mb-5">
                      <div className="w-20 h-20 bg-neo-yellow border-[3px] border-neo-black shadow-neo-lg flex items-center justify-center rounded-full">
                        <Bot size={36} className="text-neo-black" />
                      </div>
                      <DecoCircle size={24} color="#00C9B1" className="-top-2 -right-2" />
                      <DecoSquare size={16} color="#FF6B6B" className="-bottom-1 -left-3" rotate={20} />
                    </div>
                    <h2 className="font-display font-bold text-xl md:text-2xl text-neo-black mb-1">
                      Hi! I'm <span className="bg-neo-yellow px-2 border-2 border-neo-black inline-block">HRAgent AI</span>
                    </h2>
                    <p className="font-mono text-xs text-gray-500 max-w-md mt-2">
                      Your intelligent HR assistant — ask me about leave, attendance, policies, performance, and more.
                    </p>

                    {!voiceMode && (
                      <button
                        onClick={() => setVoiceMode(true)}
                        className="mt-4 flex items-center gap-2 px-4 py-2 border-2 border-neo-black bg-neo-teal/20
                          hover:bg-neo-teal shadow-neo-sm hover:shadow-none hover:translate-x-[2px] hover:translate-y-[2px]
                          transition-all font-mono text-xs"
                      >
                        <Mic size={14} />
                        Try voice conversation
                      </button>
                    )}

                    <div className="grid grid-cols-2 md:grid-cols-3 gap-2.5 mt-6 w-full max-w-lg">
                      {QUICK_PROMPTS.map(p => (
                        <button
                          key={p.text}
                          onClick={() => send(p.text)}
                          disabled={isBusy}
                          className="group flex items-start gap-2 text-left p-3 border-2 border-neo-black bg-white
                            shadow-neo-sm hover:shadow-none hover:translate-x-[2px] hover:translate-y-[2px]
                            hover:bg-neo-yellow transition-all disabled:opacity-40"
                        >
                          <span className="text-base flex-shrink-0 mt-0.5">{p.icon}</span>
                          <span className="font-mono text-[11px] leading-tight text-neo-black">{p.text}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {/* Chat messages */}
                {messages.map(m => (
                  <div key={m.id} className={`flex gap-3 ${m.role === 'user' ? 'flex-row-reverse' : ''} ${m.id.startsWith('init') && isFirstMessage ? 'hidden' : ''}`}>
                    {/* Avatar */}
                    <div className="flex-shrink-0 mt-1">
                      {m.role === 'user' ? (
                        <div className="w-9 h-9 bg-neo-yellow border-2 border-neo-black shadow-neo-sm flex items-center justify-center rounded-full">
                          {m.id.startsWith('vu-') ? <Mic size={14} className="text-neo-black" /> : <User size={16} className="text-neo-black" />}
                        </div>
                      ) : (
                        <div className="w-9 h-9 bg-neo-black border-2 border-neo-black shadow-neo-sm flex items-center justify-center rounded-full">
                          <Bot size={16} className="text-neo-yellow" />
                        </div>
                      )}
                    </div>

                    {/* Bubble */}
                    <div className={`max-w-[78%] flex flex-col gap-1 ${m.role === 'user' ? 'items-end' : ''}`}>
                      <div
                        className={`border-2 border-neo-black px-4 py-3 font-mono text-sm leading-relaxed
                          ${m.role === 'user'
                            ? 'bg-neo-yellow shadow-neo-sm rounded-tl-2xl rounded-bl-2xl rounded-br-2xl whitespace-pre-wrap'
                            : 'bg-white shadow-neo-sm rounded-tr-2xl rounded-br-2xl rounded-bl-2xl'}`}
                      >
                        {m.role === 'assistant' && m.id === typingMsgId ? (
                          <TypewriterText
                            text={m.content}
                            speed={18}
                            onComplete={() => setTypingMsgId(null)}
                          />
                        ) : m.role === 'assistant' ? (
                          <MarkdownContent>{m.content}</MarkdownContent>
                        ) : (
                          m.content
                        )}
                      </div>
                      <span className="font-mono text-[10px] text-gray-400 px-1">{formatTime(m.timestamp)}</span>
                    </div>
                  </div>
                ))}

                {/* Typing / voice processing indicator */}
                {(loading || voiceLoading) && (
                  <div className="flex gap-3">
                    <div className="w-9 h-9 bg-neo-black border-2 border-neo-black shadow-neo-sm flex items-center justify-center flex-shrink-0 rounded-full">
                      <Bot size={16} className="text-neo-yellow" />
                    </div>
                    <div className="border-2 border-neo-black bg-white px-5 py-3.5 flex gap-2 items-center shadow-neo-sm rounded-tr-2xl rounded-br-2xl rounded-bl-2xl">
                      {voiceLoading ? (
                        <span className="font-mono text-xs text-gray-500 flex items-center gap-2">
                          <span className="typing-dot w-2 h-2 bg-neo-teal rounded-full" />
                          <span className="typing-dot w-2 h-2 bg-neo-yellow rounded-full" />
                          <span className="typing-dot w-2 h-2 bg-neo-coral rounded-full" />
                          <span className="ml-1">Processing voice...</span>
                        </span>
                      ) : (
                        <>
                          <span className="typing-dot w-2.5 h-2.5 bg-neo-teal rounded-full" />
                          <span className="typing-dot w-2.5 h-2.5 bg-neo-yellow rounded-full" />
                          <span className="typing-dot w-2.5 h-2.5 bg-neo-coral rounded-full" />
                        </>
                      )}
                    </div>
                  </div>
                )}
              </>
            )}
            <div ref={bottomRef} />
          </div>
        </div>

        {/* Sources strip */}
        {sources.length > 0 && (
          <div className="border-t-2 border-neo-black px-4 py-2 flex items-center gap-2 bg-neo-teal/10 flex-shrink-0">
            <div className="w-6 h-6 bg-neo-teal border-2 border-neo-black flex items-center justify-center flex-shrink-0 rounded-full">
              <FileText size={10} className="text-neo-black" />
            </div>
            <p className="font-mono text-xs text-gray-600">
              <span className="font-bold text-neo-black">Sources:</span> {sources.join(' \u00B7 ')}
            </p>
          </div>
        )}

        {/* Audio playing indicator */}
        {isPlaying && (
          <div className="border-t-2 border-neo-black px-4 py-2 flex items-center justify-between bg-neo-black flex-shrink-0">
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-1">
                {[...Array(5)].map((_, i) => (
                  <div
                    key={i}
                    className="w-1 bg-neo-yellow rounded-full"
                    style={{
                      height: `${8 + Math.random() * 16}px`,
                      animation: `pulse 0.${4 + i}s ease-in-out infinite alternate`,
                    }}
                  />
                ))}
              </div>
              <span className="font-mono text-xs text-neo-yellow">AI is speaking...</span>
            </div>
            <button
              onClick={stopAudio}
              className="p-1.5 border-2 border-neo-yellow bg-transparent hover:bg-neo-coral hover:border-neo-coral text-neo-yellow hover:text-white transition-all"
              title="Stop audio"
            >
              <VolumeX size={12} />
            </button>
          </div>
        )}

        {/* ── Stop Response Button ── shown when AI is generating/typing/speaking */}
        {canStop && (
          <div className="border-t-2 border-neo-black flex justify-center py-2 bg-neo-bg/80 flex-shrink-0">
            <button
              onClick={stopResponse}
              className="flex items-center gap-2 px-5 py-2 border-2 border-neo-black bg-neo-coral text-white
                shadow-neo-sm hover:shadow-none hover:translate-x-[2px] hover:translate-y-[2px]
                transition-all font-display font-bold text-xs uppercase tracking-wider"
            >
              <CircleStop size={14} />
              Stop
            </button>
          </div>
        )}

        {/* Quick prompts strip */}
        {!isFirstMessage && !voiceMode && !canStop && (
          <div className="border-t-2 border-neo-black px-3 py-2 flex gap-2 overflow-x-auto flex-shrink-0 bg-neo-bg/50">
            {QUICK_PROMPTS.map(p => (
              <button
                key={p.text}
                onClick={() => send(p.text)}
                disabled={isBusy}
                className="flex-shrink-0 text-[11px] font-mono border-2 border-neo-black px-2.5 py-1 bg-white
                  hover:bg-neo-yellow shadow-neo-sm hover:shadow-none hover:translate-x-[1px] hover:translate-y-[1px]
                  transition-all disabled:opacity-40 flex items-center gap-1.5"
              >
                <span>{p.icon}</span> {p.text}
              </button>
            ))}
          </div>
        )}

        {/* ── Input Area ── */}
        {voiceMode ? (
          <div className="border-t-2 border-neo-black bg-neo-bg flex flex-col items-center gap-3 py-4 px-4 flex-shrink-0">
            {isRecording && (
              <div className="w-full max-w-sm">
                <VoiceWaveform isRecording={isRecording} analyser={analyser} />
              </div>
            )}

            <div className="flex items-center gap-4">
              <button
                onClick={() => { setVoiceMode(false); if (isRecording) stopRecording(); }}
                className="p-2.5 border-2 border-neo-black bg-white hover:bg-neo-yellow shadow-neo-sm
                  hover:shadow-none hover:translate-x-[2px] hover:translate-y-[2px] transition-all"
                title="Switch to text input"
              >
                <MessageSquare size={16} />
              </button>

              <button
                onClick={isRecording ? stopRecording : startRecording}
                disabled={voiceLoading}
                className="relative group disabled:opacity-50"
                title={isRecording ? 'Stop recording' : 'Start recording'}
              >
                {isRecording && <PulseRing />}
                <div className={`relative w-16 h-16 rounded-full border-[3px] border-neo-black flex items-center justify-center
                  transition-all duration-200 shadow-neo
                  ${isRecording
                    ? 'bg-neo-coral scale-110'
                    : 'bg-neo-teal hover:bg-neo-yellow hover:scale-105'
                  }
                  ${voiceLoading ? 'animate-pulse' : ''}
                `}>
                  {isRecording ? (
                    <Square size={24} className="text-white" fill="white" />
                  ) : voiceLoading ? (
                    <div className="flex gap-1">
                      <span className="typing-dot w-2 h-2 bg-white rounded-full" />
                      <span className="typing-dot w-2 h-2 bg-white rounded-full" />
                      <span className="typing-dot w-2 h-2 bg-white rounded-full" />
                    </div>
                  ) : (
                    <Mic size={28} className="text-neo-black" />
                  )}
                </div>
              </button>

              <button
                onClick={isPlaying ? stopAudio : undefined}
                className={`p-2.5 border-2 border-neo-black shadow-neo-sm
                  hover:shadow-none hover:translate-x-[2px] hover:translate-y-[2px] transition-all
                  ${isPlaying ? 'bg-neo-coral text-white' : 'bg-white hover:bg-neo-yellow'}`}
                title={isPlaying ? 'Stop playback' : 'Speaker'}
              >
                {isPlaying ? <VolumeX size={16} /> : <Volume2 size={16} />}
              </button>
            </div>

            <p className="font-mono text-[11px] text-gray-500">
              {isRecording
                ? 'Listening... tap the button to stop'
                : voiceLoading
                  ? 'Processing your voice...'
                  : 'Tap the microphone to start speaking'
              }
            </p>
          </div>
        ) : (
          <div className="border-t-2 border-neo-black flex flex-shrink-0 bg-white">
            <div className="flex items-center pl-4">
              <Sparkles size={16} className="text-neo-teal" />
            </div>
            <input
              ref={inputRef}
              className="flex-1 px-3 py-3.5 font-mono text-sm outline-none bg-transparent border-none placeholder:text-gray-400"
              placeholder="Ask me anything about HR..."
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && !e.shiftKey && send(input)}
              disabled={isBusy}
            />
            <button
              onClick={() => { setVoiceMode(true); startRecording(); }}
              disabled={isBusy}
              className="px-3 hover:bg-neo-teal/20 transition-colors flex items-center disabled:opacity-40"
              title="Voice input"
            >
              <Mic size={16} className="text-gray-500 hover:text-neo-teal" />
            </button>
            <button
              onClick={() => send(input)}
              disabled={!input.trim() || isBusy}
              className="px-5 bg-neo-teal border-l-2 border-neo-black hover:bg-neo-yellow
                disabled:opacity-40 disabled:cursor-not-allowed transition-all flex items-center gap-2
                font-display font-bold text-xs uppercase tracking-wider"
            >
              <Send size={16} />
              <span className="hidden md:inline">Send</span>
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
