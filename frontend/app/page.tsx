'use client';
import React from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { 
  Zap, Database, Mic, Layers, Bell, ShieldCheck, 
  ArrowRight, CheckCircle2, TrendingUp, Award, Sparkles, Globe, Download
} from 'lucide-react';

export default function LandingPage() {
  const router = useRouter();

  return (
    <div className="min-h-screen theme-bg-main theme-text-main flex flex-col justify-between selection:bg-yellow-500 selection:text-slate-950">
      {/* Top Navbar */}
      <header className="w-full border-b theme-border px-8 py-5 flex items-center justify-between max-w-[1400px] mx-auto">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-yellow-500 to-amber-400 flex items-center justify-center text-slate-950 font-black text-2xl shadow-lg shadow-yellow-500/20">
            B
          </div>
          <div>
            <span className="font-extrabold text-xl tracking-tight theme-text-main block leading-none">
              Bizpanion
            </span>
            <span className="text-[10px] font-mono font-bold tracking-widest text-yellow-500 uppercase mt-1 block">
              Autonomous Business Cockpit
            </span>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <Link
            href="/onboarding"
            className="text-xs font-bold theme-text-muted hover:theme-text-main transition-colors"
          >
            Onboarding
          </Link>
          <button
            onClick={() => router.push('/home')}
            className="bg-yellow-500 hover:bg-yellow-400 text-slate-950 font-bold text-xs px-5 py-2.5 rounded-xl shadow-lg shadow-yellow-500/20 transition-all hover:scale-[1.02] flex items-center gap-2"
          >
            <span>Launch Cockpit</span>
            <ArrowRight size={14} />
          </button>
        </div>
      </header>

      {/* Hero Section */}
      <main className="max-w-[1200px] mx-auto px-6 py-16 text-center space-y-8 animate-fade-in flex-1 flex flex-col justify-center">
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-yellow-500/10 border border-yellow-500/20 text-yellow-500 text-xs font-mono font-bold uppercase tracking-wider mx-auto">
          <Sparkles size={14} /> Powering Indian Kirana, Dairy, Textile & Produce Enterprises
        </div>

        <h1 className="text-4xl sm:text-6xl font-extrabold tracking-tight max-w-4xl mx-auto leading-tight">
          Autonomous Business Cockpit for <span className="bg-gradient-to-r from-yellow-400 to-amber-500 bg-clip-text text-transparent">Indian MSMEs</span>
        </h1>

        <p className="text-base sm:text-lg theme-text-muted max-w-2xl mx-auto leading-relaxed">
          Connect your local Tally Prime on Port 9000, run PyTorch deep learning demand forecasts, benchmark Agmarknet wholesale prices, and dispatch automated WhatsApp action notices.
        </p>

        <div className="flex items-center justify-center gap-4 flex-wrap pt-4">
          <button
            onClick={() => router.push('/home')}
            className="bg-yellow-500 hover:bg-yellow-400 text-slate-950 font-bold text-sm px-8 py-4 rounded-2xl shadow-xl shadow-yellow-500/25 transition-all hover:scale-105 flex items-center gap-3"
          >
            <span>Launch Dashboard Cockpit</span>
            <ArrowRight size={18} />
          </button>

          <button
            onClick={() => router.push('/talking-space')}
            className="theme-bg-card border theme-border hover:border-yellow-500/50 theme-text-main font-bold text-sm px-7 py-4 rounded-2xl transition-all flex items-center gap-2"
          >
            <Mic size={18} className="text-yellow-500" />
            <span>Try Voice Copilot</span>
          </button>
        </div>

        {/* Feature Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-16 text-left">
          <div className="theme-bg-card border theme-border p-6 rounded-3xl space-y-3 hover:border-yellow-500/40 transition-all shadow-xl">
            <div className="w-10 h-10 rounded-2xl bg-yellow-500/10 text-yellow-500 flex items-center justify-center border border-yellow-500/20">
              <Database size={20} />
            </div>
            <h3 className="font-bold text-lg theme-text-main">Tally Prime 9000 Ingestion</h3>
            <p className="text-xs theme-text-muted leading-relaxed">
              Direct HTTP XML protocol integration with Tally Prime 9000 for automated DayBook ledger extraction and voucher reconciliation.
            </p>
          </div>

          <div className="theme-bg-card border theme-border p-6 rounded-3xl space-y-3 hover:border-yellow-500/40 transition-all shadow-xl">
            <div className="w-10 h-10 rounded-2xl bg-yellow-500/10 text-yellow-500 flex items-center justify-center border border-yellow-500/20">
              <TrendingUp size={20} />
            </div>
            <h3 className="font-bold text-lg theme-text-main">PyTorch Demand Forecasting</h3>
            <p className="text-xs theme-text-muted leading-relaxed">
              Custom 2-layer LSTM deep learning neural network trained on sequential retail sales data for 7-day stock velocity forecasting.
            </p>
          </div>

          <div className="theme-bg-card border theme-border p-6 rounded-3xl space-y-3 hover:border-yellow-500/40 transition-all shadow-xl">
            <div className="w-10 h-10 rounded-2xl bg-yellow-500/10 text-yellow-500 flex items-center justify-center border border-yellow-500/20">
              <Mic size={20} />
            </div>
            <h3 className="font-bold text-lg theme-text-main">Multilingual Voice Copilot</h3>
            <p className="text-xs theme-text-muted leading-relaxed">
              Native voice intelligence supporting spoken Hindi, English, Tamil, Telugu, and Kannada with instant gTTS audio responses.
            </p>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="w-full border-t theme-border py-6 text-center text-xs theme-text-muted font-mono">
        Bizpanion Autonomous Cockpit • Powered by PyTorch & Featherless.ai
      </footer>
    </div>
  );
}
