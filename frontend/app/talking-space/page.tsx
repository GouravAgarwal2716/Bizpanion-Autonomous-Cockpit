'use client';
import React, { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { 
  Mic, Volume2, VolumeX, Sparkles, Send, RefreshCw, 
  CheckCircle2
} from 'lucide-react';
import NavSidebar from '@/components/NavSidebar';
import { 
  getStoredBusinessId, 
  startVoiceSession, 
  sendVoiceTurn,
  getApiUrl,
} from '@/lib/api';
import { getLang, type Lang, LANGUAGE_NAMES, t } from '@/lib/i18n';

interface Message {
  role: 'assistant' | 'user';
  text: string;
  audio_url?: string;
  timestamp: string;
}

const QUICK_PROMPTS = [
  "How are my business sales performing today?",
  "Compare my selling rates against regional Mandi modal prices.",
  "Which government subsidies can I apply for right now?",
  "What is my biggest risk alert and how do I solve it?",
  "Suggest a safe pricing strategy to increase profit margins."
];

export default function TalkingSpacePage() {
  const router = useRouter();
  const [lang, setLang] = useState<Lang>('en');
  const [businessId, setBusinessId] = useState('');
  const [sessionId, setSessionId] = useState('');
  const [status, setStatus] = useState<'idle' | 'listening' | 'thinking' | 'speaking'>('idle');
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputVal, setInputVal] = useState('');
  const [isMuted, setIsMuted] = useState(false);

  const recognitionRef = useRef<any>(null);
  const audioPlayerRef = useRef<HTMLAudioElement | null>(null);
  const chatBottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const bid = getStoredBusinessId();
    if (!bid) {
      router.push('/onboarding');
      return;
    }
    setBusinessId(bid);
    
    const updateLang = () => {
      const l = getLang();
      setLang(l);
    };
    updateLang();

    if (typeof window !== 'undefined') {
      window.addEventListener('languageChange', updateLang);
    }

    initSession(bid, getLang());

    return () => {
      if (typeof window !== 'undefined') {
        window.removeEventListener('languageChange', updateLang);
      }
    };
  }, []);

  useEffect(() => {
    if (chatBottomRef.current) {
      chatBottomRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, status]);

  async function initSession(bid: string, sessionLang: Lang) {
    setStatus('thinking');
    try {
      const data = await startVoiceSession(bid, sessionLang);
      setSessionId(data.session_id);
      
      const welcomeMsg = data.greeting || 'Namaste! I am your Autonomous Business Copilot. How can I help your enterprise today?';
      setMessages([
        {
          role: 'assistant',
          text: welcomeMsg,
          audio_url: data.greeting_audio_url,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        }
      ]);

      if (data.greeting_audio_url && !isMuted) {
        playAudioResponse(data.greeting_audio_url);
      } else {
        setStatus('idle');
      }
    } catch {
      setStatus('idle');
    }
  }

  function playAudioResponse(url: string) {
    setStatus('speaking');
    if (audioPlayerRef.current) {
      audioPlayerRef.current.pause();
    }

    const API_URL = getApiUrl();
    const fullUrl = url.startsWith('http') ? url : `${API_URL}${url}`;
    const audio = new Audio(fullUrl);
    audioPlayerRef.current = audio;

    audio.onended = () => setStatus('idle');
    audio.onerror = () => setStatus('idle');

    audio.play().catch(() => setStatus('idle'));
  }

  async function handleSendTurn(textToSend?: string) {
    const text = (textToSend || inputVal).trim();
    if (!text || status === 'thinking' || status === 'speaking') return;

    setInputVal('');
    const userMsg: Message = {
      role: 'user',
      text,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages(prev => [...prev, userMsg]);
    setStatus('thinking');

    try {
      const response = await sendVoiceTurn({
        session_id: sessionId,
        business_id: businessId,
        user_speech: text,
        language: lang
      });
      const assistantMsg: Message = {
        role: 'assistant',
        text: response.reply_text,
        audio_url: response.audio_url,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };

      setMessages(prev => [...prev, assistantMsg]);

      if (response.audio_url && !isMuted) {
        playAudioResponse(response.audio_url);
      } else {
        setStatus('idle');
      }
    } catch (e: any) {
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          text: `Error processing request: ${e.message}`,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        }
      ]);
      setStatus('idle');
    }
  }

  function startListening() {
    if (typeof window === 'undefined') return;
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (!SpeechRecognition) {
      alert('Speech recognition is not supported in this browser. Please type your query.');
      return;
    }

    if (status === 'listening') {
      if (recognitionRef.current) recognitionRef.current.stop();
      setStatus('idle');
      return;
    }

    try {
      const recognition = new SpeechRecognition();
      recognitionRef.current = recognition;
      recognition.continuous = false;
      recognition.interimResults = false;

      const langMap: Record<string, string> = {
        en: 'en-IN', hi: 'hi-IN', ta: 'ta-IN', te: 'te-IN', kn: 'kn-IN'
      };
      recognition.lang = langMap[lang] || 'en-IN';

      recognition.onstart = () => setStatus('listening');
      recognition.onresult = (event: any) => {
        const transcript = event.results[0][0].transcript;
        if (transcript) {
          handleSendTurn(transcript);
        }
      };
      recognition.onerror = () => setStatus('idle');
      recognition.onend = () => {
        setStatus('idle');
      };

      recognition.start();
    } catch {
      setStatus('idle');
    }
  }

  return (
    <div className="flex min-h-screen theme-bg-main">
      <NavSidebar active="talking" lang={lang} />

      <main className="ml-64 flex-1 min-h-screen p-8 max-w-[1100px] mx-auto flex flex-col justify-between">
        {/* Top Header & Language Selector */}
        <div className="flex items-center justify-between mb-6 flex-wrap gap-4 animate-fade-in">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-yellow-500/10 border border-yellow-500/20 text-yellow-500 text-xs font-mono font-bold uppercase tracking-wider mb-2">
              <Sparkles size={13} /> Gemini Live Copilot Agent
            </div>
            <h1 className="text-3xl font-extrabold theme-text-main tracking-tight">
              {t('nav.talking', lang)}
            </h1>
            <p className="text-sm theme-text-muted mt-1">
              Speak directly in your native Indian dialect to query inventory, Mandi prices, and credit schemes.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <select
              value={lang}
              onChange={(e) => {
                const newLang = e.target.value as Lang;
                setLang(newLang);
                if (businessId) initSession(businessId, newLang);
              }}
              className="px-3 py-2 rounded-xl theme-bg-card border theme-border theme-text-main text-xs font-bold outline-none cursor-pointer"
            >
              {Object.entries(LANGUAGE_NAMES).map(([code, name]) => (
                <option key={code} value={code}>{name}</option>
              ))}
            </select>

            <button
              onClick={() => setIsMuted(!isMuted)}
              className="p-2.5 rounded-xl theme-bg-card border theme-border theme-text-main hover:text-yellow-500 transition-colors"
              title={isMuted ? 'Unmute Audio' : 'Mute Audio'}
            >
              {isMuted ? <VolumeX size={16} /> : <Volume2 size={16} />}
            </button>
          </div>
        </div>

        {/* Centered Main Voice Interactive Agent Orb */}
        <div className="my-auto py-8 text-center space-y-6 animate-fade-in">
          {/* Animated Glowing Voice Orb */}
          <div className="relative w-36 h-36 mx-auto flex items-center justify-center">
            <div className={`absolute inset-0 rounded-full transition-all duration-500 ${
              status === 'listening' 
                ? 'bg-yellow-500/30 animate-ping' 
                : status === 'speaking' 
                ? 'bg-blue-500/30 animate-pulse' 
                : 'bg-yellow-500/10'
            }`} />

            <button
              onClick={startListening}
              className={`relative z-10 w-28 h-28 rounded-full flex items-center justify-center transition-all duration-300 shadow-2xl ${
                status === 'listening'
                  ? 'bg-yellow-500 text-slate-950 scale-110 shadow-yellow-500/50'
                  : status === 'speaking'
                  ? 'bg-blue-500 text-slate-950 scale-105 shadow-blue-500/50'
                  : 'bg-gradient-to-tr from-yellow-400 to-amber-500 text-slate-950 hover:scale-105 shadow-yellow-500/30'
              }`}
            >
              {status === 'thinking' ? (
                <RefreshCw size={36} className="animate-spin" />
              ) : (
                <Mic size={36} />
              )}
            </button>
          </div>

          {/* Status Label */}
          <div>
            <h3 className="text-xl font-bold theme-text-main">
              {status === 'listening' ? 'Listening to your voice...' : status === 'speaking' ? 'Copilot Speaking...' : status === 'thinking' ? 'Analyzing enterprise data...' : 'Click Microphone to Start Speaking'}
            </h3>
            <p className="text-xs theme-text-muted mt-1">
              Supports spoken Hindi, English, Tamil, Telugu, and Kannada.
            </p>
          </div>

          {/* Quick Prompt Suggestion Pills */}
          <div className="flex flex-wrap justify-center gap-2 max-w-2xl mx-auto pt-2">
            {QUICK_PROMPTS.map((prompt, idx) => (
              <button
                key={idx}
                onClick={() => handleSendTurn(prompt)}
                className="px-3 py-1.5 rounded-full theme-bg-card border theme-border hover:border-yellow-500/40 text-xs theme-text-muted hover:theme-text-main transition-all text-left"
              >
                "{prompt}"
              </button>
            ))}
          </div>
        </div>

        {/* Conversation Turn Log Drawer */}
        <div className="theme-bg-card border theme-border rounded-3xl p-6 shadow-xl space-y-4 max-h-[280px] overflow-y-auto">
          <div className="flex items-center justify-between border-b theme-border pb-3">
            <h4 className="font-bold text-xs font-mono uppercase tracking-wider theme-text-main flex items-center gap-2">
              <CheckCircle2 size={14} className="text-yellow-500" /> Voice Conversation Transcript
            </h4>
            <span className="text-[10px] font-mono theme-text-muted">{messages.length} Turn Messages</span>
          </div>

          <div className="space-y-3">
            {messages.map((msg, idx) => (
              <div
                key={idx}
                className={`p-3.5 rounded-2xl text-xs max-w-[85%] leading-relaxed ${
                  msg.role === 'user'
                    ? 'ml-auto bg-yellow-500 text-slate-950 font-medium'
                    : 'theme-bg-input border theme-border theme-text-main'
                }`}
              >
                <div className="font-bold text-[10px] uppercase opacity-75 mb-1">
                  {msg.role === 'user' ? 'You (Voice)' : 'Bizpanion Copilot'} • {msg.timestamp}
                </div>
                <div>{msg.text}</div>
              </div>
            ))}
            <div ref={chatBottomRef} />
          </div>
        </div>

        {/* Bottom Input Box */}
        <div className="mt-4 flex items-center gap-2">
          <input
            type="text"
            value={inputVal}
            onChange={(e) => setInputVal(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSendTurn()}
            placeholder="Or type a business query here..."
            className="flex-1 px-4 py-3 rounded-2xl theme-bg-card border theme-border theme-text-main text-xs outline-none focus:border-yellow-500/50"
          />
          <button
            onClick={() => handleSendTurn()}
            className="p-3 rounded-2xl bg-yellow-500 hover:bg-yellow-400 text-slate-950 font-bold transition-all shadow-md"
          >
            <Send size={16} />
          </button>
        </div>

      </main>
    </div>
  );
}
