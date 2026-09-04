'use client';
import React, { useState, useEffect, useRef } from 'react';
import { Mic, MicOff, Volume2, VolumeX, X, Sparkles, ExternalLink, ShieldCheck, ArrowRight } from 'lucide-react';
import { startVoiceSession, sendVoiceTurn } from '@/lib/api';
import { t, type Lang } from '@/lib/i18n';

interface VoiceLiveModalProps {
  isOpen: boolean;
  onClose: () => void;
  businessId: string;
  initialLang?: Lang;
}

interface Message {
  role: 'assistant' | 'user';
  text: string;
  audio_url?: string;
  timestamp: string;
  schemes?: any[];
}

export default function VoiceLiveModal({ isOpen, onClose, businessId, initialLang = 'en' }: VoiceLiveModalProps) {
  const [lang, setLang] = useState<Lang>(initialLang);
  const [sessionId, setSessionId] = useState<string>('');
  const [status, setStatus] = useState<'idle' | 'listening' | 'thinking' | 'speaking'>('idle');
  const [messages, setMessages] = useState<Message[]>([]);
  const [isMuted, setIsMuted] = useState(false);
  const [transcriptPreview, setTranscriptPreview] = useState('');
  
  const recognitionRef = useRef<any>(null);
  const audioPlayerRef = useRef<HTMLAudioElement | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isOpen && businessId) {
      initSession();
    } else {
      stopListening();
      if (audioPlayerRef.current) {
        audioPlayerRef.current.pause();
      }
    }
  }, [isOpen, businessId]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, transcriptPreview]);

  async function initSession() {
    setStatus('thinking');
    try {
      const data = await startVoiceSession(businessId, lang);
      setSessionId(data.session_id);
      const welcomeMsg: Message = {
        role: 'assistant',
        text: data.welcome_text,
        audio_url: data.audio_url,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages([welcomeMsg]);
      // Do not auto-play voice in the background without user interaction
      setStatus('idle');
    } catch (e) {
      console.error('Failed to start voice session', e);
      setStatus('idle');
    }
  }

  function playAssistantAudio(url: string, text?: string) {
    setStatus('speaking');
    const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    const fullUrl = url ? (url.startsWith('http') ? url : `${API_URL}${url}`) : '';
    
    if (audioPlayerRef.current) {
      audioPlayerRef.current.pause();
    }

    if (!fullUrl) {
      speakViaSynthesis(text || '');
      return;
    }

    const audio = new Audio(fullUrl);
    audioPlayerRef.current = audio;
    audio.play().catch(() => {
      // Audio autoplay blocked by browser policy or format issue -> fallback to synthesis
      speakViaSynthesis(text || '');
    });

    audio.onended = () => {
      setStatus('idle');
      startListening();
    };

    audio.onerror = () => {
      speakViaSynthesis(text || '');
    };
  }

  function speakViaSynthesis(text: string) {
    if (typeof window === 'undefined' || !window.speechSynthesis || !text) {
      setStatus('idle');
      startListening();
      return;
    }
    try {
      window.speechSynthesis.cancel();
      const u = new SpeechSynthesisUtterance(text);
      u.lang = getSpeechLangCode(lang);
      u.rate = 1.0;
      u.onend = () => {
        setStatus('idle');
        startListening();
      };
      u.onerror = () => {
        setStatus('idle');
        startListening();
      };
      window.speechSynthesis.speak(u);
    } catch {
      setStatus('idle');
      startListening();
    }
  }

  function getSpeechLangCode(l: Lang): string {
    switch (l) {
      case 'hi': return 'hi-IN';
      case 'ta': return 'ta-IN';
      case 'te': return 'te-IN';
      case 'kn': return 'kn-IN';
      default: return 'en-IN';
    }
  }

  function startListening() {
    if (typeof window === 'undefined') return;

    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setStatus('idle');
      return;
    }

    try {
      const recognition = new SpeechRecognition();
      recognitionRef.current = recognition;
      recognition.continuous = false;
      recognition.interimResults = true;
      recognition.lang = getSpeechLangCode(lang);

      recognition.onstart = () => {
        setStatus('listening');
        setTranscriptPreview('');
      };

      recognition.onresult = (event: any) => {
        let interim = '';
        for (let i = event.resultIndex; i < event.results.length; ++i) {
          if (event.results[i].isFinal) {
            const finalSpeech = event.results[i][0].transcript;
            setTranscriptPreview('');
            handleUserSpeech(finalSpeech);
          } else {
            interim += event.results[i][0].transcript;
          }
        }
        setTranscriptPreview(interim);
      };

      recognition.onerror = (e: any) => {
        console.warn('Speech recognition error:', e.error);
        if (e.error !== 'no-speech') {
          setStatus('idle');
        }
      };

      recognition.onend = () => {
        if (status === 'listening') {
          setStatus('idle');
        }
      };

      recognition.start();
    } catch (e) {
      console.error(e);
      setStatus('idle');
    }
  }

  function stopListening() {
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch {}
    }
  }

  async function handleUserSpeech(speechText: string) {
    if (!speechText.trim()) return;
    
    stopListening();
    const userMsg: Message = {
      role: 'user',
      text: speechText,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };
    setMessages(prev => [...prev, userMsg]);
    setStatus('thinking');

    try {
      const res = await sendVoiceTurn({
        session_id: sessionId,
        business_id: businessId,
        user_speech: speechText,
        language: lang,
      });

      const assistantMsg: Message = {
        role: 'assistant',
        text: res.assistant_text,
        audio_url: res.audio_url,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        schemes: res.matched_schemes || [],
      };

      setMessages(prev => [...prev, assistantMsg]);

      if (res.audio_url && !isMuted) {
        playAssistantAudio(res.audio_url, res.assistant_text);
      } else {
        setStatus('idle');
        startListening();
      }
    } catch (e) {
      console.error(e);
      setStatus('idle');
      startListening();
    }
  }

  if (!isOpen) return null;

  return (
    <div 
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 1000,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: 'rgba(0,0,0,0.85)',
        backdropFilter: 'blur(16px)',
        padding: 20,
      }}
    >
      <div 
        style={{
          width: '100%',
          maxWidth: 960,
          height: '88vh',
          maxHeight: 760,
          backgroundColor: '#12141a',
          border: '1px solid rgba(255,255,255,0.12)',
          borderRadius: 24,
          boxShadow: '0 30px 80px rgba(0,0,0,0.8)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          color: '#fff',
        }}
      >
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '16px 24px', borderBottom: '1px solid rgba(255,255,255,0.08)', backgroundColor: '#1a1d26' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{ width: 40, height: 40, borderRadius: 12, background: 'linear-gradient(135deg, #6366f1, #06b6d4)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Sparkles size={20} color="#fff" />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <h3 style={{ fontSize: '1.1rem', fontWeight: 700, margin: 0, color: '#fff' }}>
                  Live Voice Companion
                </h3>
                <span style={{ fontSize: '0.68rem', padding: '2px 8px', borderRadius: 99, background: 'rgba(99,102,241,0.2)', border: '1px solid rgba(99,102,241,0.4)', color: '#818cf8', fontWeight: 700, textTransform: 'uppercase' }}>
                  Autonomous
                </span>
              </div>
              <p style={{ fontSize: '0.75rem', color: '#94a3b8', margin: 0 }}>
                Spoken business advisory with real-time reasoning
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            {/* Language Selector */}
            <select
              value={lang}
              onChange={e => setLang(e.target.value as Lang)}
              aria-label="Select spoken language"
              style={{
                backgroundColor: '#1e2230',
                border: '1px solid rgba(255,255,255,0.15)',
                color: '#f1f5f9',
                fontSize: '0.8rem',
                borderRadius: 10,
                padding: '6px 12px',
                outline: 'none',
                cursor: 'pointer'
              }}
            >
              <option value="en">English (India)</option>
              <option value="hi">हिंदी (Hindi)</option>
              <option value="ta">தமிழ் (Tamil)</option>
              <option value="te">తెలుగు (Telugu)</option>
              <option value="kn">ಕನ್ನಡ (Kannada)</option>
            </select>

            {/* Mute Toggle */}
            <button
              onClick={() => setIsMuted(!isMuted)}
              title={isMuted ? 'Unmute voice' : 'Mute voice'}
              style={{
                padding: 8,
                borderRadius: 10,
                backgroundColor: '#1e2230',
                border: '1px solid rgba(255,255,255,0.1)',
                color: isMuted ? '#ef4444' : '#06b6d4',
                cursor: 'pointer'
              }}
            >
              {isMuted ? <VolumeX size={18} /> : <Volume2 size={18} />}
            </button>

            {/* Close Button */}
            <button
              onClick={onClose}
              title="Close Voice Modal"
              style={{
                padding: 8,
                borderRadius: 10,
                backgroundColor: 'rgba(255,255,255,0.06)',
                border: 'none',
                color: '#94a3b8',
                cursor: 'pointer'
              }}
            >
              <X size={18} />
            </button>
          </div>
        </div>

        {/* Central Split Layout */}
        <div style={{ width: '50%', display: 'flex', flexDirection: 'column', height: '100%', backgroundColor: 'rgba(10,11,15,0.7)' }}>
            <div style={{ padding: '12px 20px', borderBottom: '1px solid rgba(255,255,255,0.08)', backgroundColor: '#1a1d26', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span style={{ fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em', color: '#94a3b8' }}>
                Session Advisory Transcript
              </span>
              <span style={{ fontSize: '0.7rem', color: '#64748b' }}>
                {messages.length} exchanges stored
              </span>
            </div>

            {/* Transcript Messages Feed */}
            <div ref={scrollRef} style={{ flex: 1, padding: 20, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 14 }}>
              {messages.map((m, idx) => {
                const isUser = m.role === 'user';
                return (
                  <div key={idx} style={{ display: 'flex', flexDirection: 'column', alignItems: isUser ? 'flex-end' : 'flex-start', gap: 4 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.7rem', color: '#64748b' }}>
                      <span>{isUser ? 'You' : 'Bizpanion AI'}</span>
                      <span>•</span>
                      <span>{m.timestamp}</span>
                    </div>

                    <div
                      style={{
                        maxWidth: '85%',
                        borderRadius: isUser ? '18px 4px 18px 18px' : '4px 18px 18px 18px',
                        padding: '12px 16px',
                        fontSize: '0.85rem',
                        lineHeight: 1.5,
                        backgroundColor: isUser ? 'rgba(6,182,212,0.15)' : '#1e2230',
                        border: isUser ? '1px solid rgba(6,182,212,0.3)' : '1px solid rgba(255,255,255,0.1)',
                        color: isUser ? '#67e8f9' : '#f1f5f9',
                        boxShadow: '0 4px 14px rgba(0,0,0,0.3)'
                      }}
                    >
                      <p style={{ margin: 0 }}>{m.text}</p>

                      {/* Matched RAG Schemes Badge */}
                      {m.schemes && m.schemes.length > 0 && (
                        <div style={{ marginTop: 10, paddingTop: 10, borderTop: '1px solid rgba(255,255,255,0.1)', display: 'flex', flexDirection: 'column', gap: 6 }}>
                          <div style={{ fontSize: '0.72rem', fontWeight: 700, color: '#06b6d4', display: 'flex', alignItems: 'center', gap: 6 }}>
                            <ShieldCheck size={14} /> Verified Scheme Citations:
                          </div>
                          {m.schemes.map((s, sIdx) => (
                            <div
                              key={sIdx}
                              style={{
                                padding: '8px 12px',
                                borderRadius: 8,
                                backgroundColor: 'rgba(0,0,0,0.3)',
                                border: '1px solid rgba(255,255,255,0.06)',
                                fontSize: '0.75rem',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'space-between',
                                gap: 8
                              }}
                            >
                              <div style={{ overflow: 'hidden' }}>
                                <p style={{ fontWeight: 600, color: '#f1f5f9', margin: 0 }}>{s.scheme_name}</p>
                                <p style={{ fontSize: '0.7rem', color: '#94a3b8', margin: '2px 0 0 0' }}>{s.benefit}</p>
                              </div>
                              {s.apply_url && (
                                <a
                                  href={s.apply_url}
                                  target="_blank"
                                  rel="noreferrer"
                                  style={{ padding: 6, borderRadius: 6, backgroundColor: 'rgba(6,182,212,0.15)', color: '#06b6d4', display: 'flex', alignItems: 'center', textDecoration: 'none' }}
                                  title="Open Official Portal"
                                >
                                  <ExternalLink size={12} />
                                </a>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Quick Prompt Suggesters (Zero-type voice cues) */}
            <div style={{ padding: 14, borderTop: '1px solid rgba(255,255,255,0.08)', backgroundColor: '#1a1d26' }}>
              <p style={{ fontSize: '0.7rem', textTransform: 'uppercase', fontWeight: 700, color: '#64748b', margin: '0 0 8px 4px' }}>
                Suggested questions to speak:
              </p>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                {[
                  'What price should I sell onion today?',
                  'Will I run out of tomato stock soon?',
                  'Which government loan subsidy can I get?',
                ].map((sug, sIdx) => (
                  <button
                    key={sIdx}
                    onClick={() => handleUserSpeech(sug)}
                    style={{
                      fontSize: '0.75rem',
                      padding: '6px 12px',
                      borderRadius: 12,
                      backgroundColor: 'rgba(255,255,255,0.04)',
                      border: '1px solid rgba(255,255,255,0.1)',
                      color: '#cbd5e1',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: 4
                    }}
                  >
                    <span>"{sug}"</span>
                    <ArrowRight size={12} color="#818cf8" />
                  </button>
                ))}
              </div>
            </div>

          </div>
      </div>
    </div>
  );
}
