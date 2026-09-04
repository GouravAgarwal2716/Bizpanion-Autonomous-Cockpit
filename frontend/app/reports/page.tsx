'use client';
import React, { useState, useEffect } from 'react';
import { Download, Play, Pause, Headphones, FileText, BarChart2 } from 'lucide-react';
import NavSidebar from '@/components/NavSidebar';
import { getStoredBusinessId, getAlerts, getDashboardOverview } from '@/lib/api';
import { generateExecutiveReportPDF } from '@/lib/pdfGenerator';
import { getLang, type Lang, t } from '@/lib/i18n';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://bizpanion-autonomous-cockpit-backend.onrender.com';

export default function ReportsPage() {
  const [lang, setLang] = useState<Lang>('en');
  const [alerts, setAlerts] = useState<any[]>([]);
  const [dashboardData, setDashboardData] = useState<any>(null);
  const [playingUrl, setPlayingUrl] = useState<string | null>(null);
  const [audioEl, setAudioEl] = useState<HTMLAudioElement | null>(null);
  const businessId = getStoredBusinessId();

  useEffect(() => {
    const updateLang = () => {
      setLang(getLang());
    };
    updateLang();
    if (typeof window !== 'undefined') {
      window.addEventListener('languageChange', updateLang);
    }
    loadData();
    return () => {
      if (typeof window !== 'undefined') {
        window.removeEventListener('languageChange', updateLang);
      }
    };
  }, []);

  async function loadData() {
    try {
      const [data, dash] = await Promise.all([
        getAlerts(businessId, 200).catch(() => ({ alerts: [] })),
        getDashboardOverview(businessId).catch(() => null),
      ]);
      setAlerts(data.alerts || []);
      setDashboardData(dash);
    } catch {}
  }

  const alertsWithAudio = alerts.filter(a => a.audio_url);

  function handlePlay(url: string) {
    if (playingUrl === url) {
      audioEl?.pause();
      setPlayingUrl(null);
      return;
    }
    const fullUrl = url.startsWith('http') ? url : `${API_URL}${url}`;
    const a = new Audio(fullUrl);
    setAudioEl(a);
    a.play();
    setPlayingUrl(url);
    a.onended = () => setPlayingUrl(null);
  }

  function handleDownloadPDF() {
    generateExecutiveReportPDF(dashboardData, businessId);
  }

  return (
    <div className="flex min-h-screen theme-bg-main">
      <NavSidebar active="reports" lang={lang} />

      <main className="ml-64 flex-1 min-h-screen p-8 max-w-[1400px]">
        {/* Header */}
        <div className="flex items-start justify-between mb-8 flex-wrap gap-4 animate-fade-in">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-yellow-500/10 border border-yellow-500/20 text-yellow-500 text-xs font-mono font-bold uppercase tracking-wider mb-2">
              <BarChart2 size={13} /> Executive Reports & Archives
            </div>
            <h1 className="text-3xl font-extrabold theme-text-main tracking-tight">
              Business Intelligence Reports
            </h1>
            <p className="text-xs theme-text-muted mt-1 max-w-xl">
              Download clean PDF executive reports, review audio briefing archives, and analyze monthly margin performance.
            </p>
          </div>

          <button
            onClick={handleDownloadPDF}
            className="flex items-center gap-2 bg-yellow-500 hover:bg-yellow-400 text-slate-950 font-bold text-xs px-4 py-2.5 rounded-xl shadow-lg shadow-yellow-500/20 transition-all hover:scale-[1.02]"
          >
            <Download size={15} />
            <span>{t('reports.download_pdf', lang)}</span>
          </button>
        </div>

        {/* Reports Content */}
        <div className="space-y-6 animate-fade-in">
          {/* Card 1: Executive PDF Reports Archive */}
          <div className="theme-bg-card border-2 border-yellow-500/40 rounded-3xl p-6 shadow-xl space-y-4">
            <div className="flex items-center justify-between flex-wrap gap-4 border-b theme-border pb-4">
              <div>
                <h3 className="text-lg font-bold theme-text-main flex items-center gap-2">
                  <FileText size={18} className="text-yellow-500" /> Executive PDF Intelligence Reports
                </h3>
                <p className="text-xs theme-text-muted mt-0.5">
                  Generated PyTorch demand forecasts, Mandi price parity audits, and MSME subsidy matching reports.
                </p>
              </div>

              <button
                onClick={handleDownloadPDF}
                className="flex items-center gap-2 bg-yellow-500 hover:bg-yellow-400 text-slate-950 font-extrabold text-xs px-5 py-2.5 rounded-xl shadow-md transition-colors"
              >
                <Download size={15} />
                <span>{t('reports.download_pdf', lang)}</span>
              </button>
            </div>

            <div className="space-y-3">
              <div className="flex items-center justify-between p-4 rounded-2xl theme-bg-input border theme-border text-xs">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-[10px] font-bold text-yellow-500 bg-yellow-500/10 px-2 py-0.5 rounded">PDF DOCUMENT</span>
                    <h4 className="font-bold theme-text-main text-sm">Monthly Executive Audit & PyTorch Demand Forecast Report</h4>
                  </div>
                  <p className="theme-text-muted mt-1">Includes 30-day turnover analysis, stockout depletion timeline, and Mandi exchange benchmarks.</p>
                </div>

                <button
                  onClick={handleDownloadPDF}
                  className="flex items-center gap-2 bg-yellow-500/10 hover:bg-yellow-500/20 text-yellow-500 font-bold px-3.5 py-2 rounded-xl border border-yellow-500/30 transition-colors shrink-0"
                >
                  <Download size={14} />
                  <span>Download PDF</span>
                </button>
              </div>
            </div>
          </div>

          {/* Card 2: Audio Briefing Archive */}
          <div className="theme-bg-card border theme-border rounded-3xl p-6 shadow-xl">
            <h3 className="text-lg font-bold theme-text-main mb-1 flex items-center gap-2">
              <Headphones size={18} className="text-yellow-500" /> {t('reports.audio_archive', lang)}
            </h3>
            <p className="text-xs theme-text-muted mb-5">
              Listen to regional voice briefings generated by gTTS and Gemini Live Copilot.
            </p>

            {alertsWithAudio.length === 0 ? (
              <div className="p-8 text-center theme-text-muted theme-bg-input rounded-2xl border theme-border">
                <FileText size={28} className="mx-auto mb-2 opacity-50" />
                <p className="text-xs">No audio briefings saved yet. Run "Voice Business Briefing" on the dashboard to generate new audio logs.</p>
              </div>
            ) : (
              <div className="space-y-3">
                {alertsWithAudio.map((a) => (
                  <div key={a.id} className="flex items-center justify-between p-4 rounded-2xl theme-bg-input border theme-border text-xs">
                    <div>
                      <h4 className="font-bold theme-text-main text-sm">{a.title}</h4>
                      <p className="theme-text-muted mt-0.5">{a.message}</p>
                    </div>

                    <button
                      onClick={() => handlePlay(a.audio_url)}
                      className="flex items-center gap-2 bg-yellow-500/10 hover:bg-yellow-500/20 text-yellow-500 font-bold px-3 py-2 rounded-xl border border-yellow-500/30 transition-colors shrink-0"
                    >
                      {playingUrl === a.audio_url ? <Pause size={14} /> : <Play size={14} />}
                      <span>{playingUrl === a.audio_url ? 'Playing...' : 'Play Audio'}</span>
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
