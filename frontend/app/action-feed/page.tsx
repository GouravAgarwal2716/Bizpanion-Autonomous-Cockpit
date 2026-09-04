'use client';
import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { 
  Check, TrendingDown, Package, FileText, 
  TrendingUp, Bell, MessageSquare, ShieldCheck, ArrowRight,
  AlertTriangle, Volume2, CheckCircle2
} from 'lucide-react';
import NavSidebar from '@/components/NavSidebar';
import { getStoredBusinessId, getAlerts, acknowledgeAlert, getProfile } from '@/lib/api';
import { getLang, type Lang, t } from '@/lib/i18n';

const ALERT_ICONS: Record<string, React.ReactNode> = {
  underpricing:    <TrendingDown size={16} />,
  stock_depletion: <Package size={16} />,
  scheme_deadline: <FileText size={16} />,
  sales_anomaly:   <TrendingUp size={16} />,
  subsidy_match:   <ShieldCheck size={16} />,
};

function getSeedAlerts(bizType = 'kirana'): any[] {
  const seeds: Record<string, any[]> = {
    kirana: [
      { id: 'ak1', title: 'Critical Underpricing Detected: Toor Dal 1kg', severity: 'high', alert_type: 'underpricing', message: 'Your selling price is ₹145/kg while the regional FMCG wholesale benchmark is ₹165/kg (13.8% below market). Margin recovery of ₹9,200/month is possible.', recommended_action: 'Increase rate to ₹158/kg in Decision Sandbox to protect gross profit.', whatsapp_sent: true, created_at: new Date(Date.now() - 1000*60*18).toISOString(), acknowledged: false },
      { id: 'ak2', title: 'Accelerating Stockout Risk: Aashirvaad Atta 5kg', severity: 'high', alert_type: 'stock_depletion', message: 'Current inventory is 6 bags. Forecasted 7-day velocity is 28 bags based on PyTorch demand model. Stock will deplete in 1.5 days.', recommended_action: 'Place 25-bag bulk distributor order today to capture 6% wholesale discount.', whatsapp_sent: true, created_at: new Date(Date.now() - 1000*60*45).toISOString(), acknowledged: false },
      { id: 'ak3', title: 'Matched Scheme: PM SVANidhi 7% Interest Subvention', severity: 'medium', alert_type: 'scheme_deadline', message: 'Your enterprise has 120+ recorded digital transactions. You are eligible for the 3rd Tranche ₹50,000 collateral-free working capital facility.', recommended_action: 'Apply on the PM SVANidhi portal with your UPI merchant QR code.', whatsapp_sent: true, created_at: new Date(Date.now() - 1000*60*180).toISOString(), acknowledged: false },
    ],
    dairy: [
      { id: 'ad1', title: 'Milk Procurement Rate Below State Federation MSP', severity: 'high', alert_type: 'underpricing', message: 'Buffalo Raw Milk selling rate of ₹58/L is below State Dairy Federation benchmark of ₹68/L. Estimated monthly margin leakage: ₹14,000.', recommended_action: 'Realize tiered pricing for high-fat content milk in Decision Sandbox.', whatsapp_sent: true, created_at: new Date(Date.now() - 1000*60*25).toISOString(), acknowledged: false },
      { id: 'ad2', title: 'Subsidized Solar Chilling Unit Match: PMFME 35% Subsidy', severity: 'medium', alert_type: 'scheme_deadline', message: 'Government PMFME scheme provides 35% credit-linked capital subsidy up to ₹10 Lakhs for micro food & milk cooling units.', recommended_action: 'Review eligibility criteria and equipment vendors in Talking Space.', whatsapp_sent: true, created_at: new Date(Date.now() - 1000*60*120).toISOString(), acknowledged: false },
    ],
  };
  return seeds[bizType.toLowerCase()] || seeds.kirana;
}

export default function ActionFeedPage() {
  const router = useRouter();
  const [lang, setLang] = useState<Lang>('en');
  const [alerts, setAlerts] = useState<any[]>([]);
  const [playingId, setPlayingId] = useState<string | null>(null);
  const [filter, setFilter] = useState<'all' | 'high' | 'medium' | 'low' | 'unread'>('all');
  const businessId = getStoredBusinessId();

  useEffect(() => { 
    const updateLang = () => {
      setLang(getLang());
    };
    updateLang();
    if (typeof window !== 'undefined') {
      window.addEventListener('languageChange', updateLang);
    }
    loadAlerts();
    return () => {
      if (typeof window !== 'undefined') {
        window.removeEventListener('languageChange', updateLang);
      }
    };
  }, []);

  async function loadAlerts() {
    try {
      const [data, prof] = await Promise.all([
        getAlerts(businessId, 100).catch(() => ({ alerts: [] })),
        getProfile(businessId).catch(() => null),
      ]);
      const fetched = data?.alerts || [];
      setAlerts(fetched.length > 0 ? fetched : getSeedAlerts(prof?.business_type || 'kirana'));
    } catch {
      setAlerts(getSeedAlerts('kirana'));
    }
  }

  async function handleAcknowledge(alertId: string) {
    try { await acknowledgeAlert(alertId); } catch {}
    setAlerts(prev => prev.map(a => a.id === alertId ? { ...a, acknowledged: true } : a));
  }

  function speakAlert(text: string, id: string) {
    if (playingId === id) {
      if (typeof window !== 'undefined' && window.speechSynthesis) window.speechSynthesis.cancel();
      setPlayingId(null); return;
    }
    if (typeof window === 'undefined' || !window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    const map: Record<string, string> = { en: 'en-IN', hi: 'hi-IN', ta: 'ta-IN', te: 'te-IN', kn: 'kn-IN' };
    u.lang = map[lang] || 'en-IN';
    u.onend = () => setPlayingId(null);
    u.onerror = () => setPlayingId(null);
    setPlayingId(id);
    window.speechSynthesis.speak(u);
  }

  const filtered = alerts.filter(a => {
    if (filter === 'all') return true;
    if (filter === 'unread') return !a.acknowledged;
    return a.severity === filter;
  });

  return (
    <div className="flex min-h-screen theme-bg-main">
      <NavSidebar active="actionfeed" lang={lang} />

      <main className="ml-64 flex-1 min-h-screen p-8 max-w-[1400px]">
        {/* Header */}
        <div className="flex items-start justify-between mb-8 flex-wrap gap-4 animate-fade-in">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-yellow-500/10 border border-yellow-500/20 text-yellow-500 text-xs font-mono font-bold uppercase tracking-wider mb-2">
              <Bell size={13} /> Autonomous Action Stream
            </div>
            <h1 className="text-3xl font-extrabold theme-text-main tracking-tight">
              {t('feed.title', lang)}
            </h1>
            <p className="text-xs theme-text-muted mt-1 max-w-xl">
              {t('feed.subtitle', lang)}
            </p>
          </div>

          {/* Filter Pills */}
          <div className="flex items-center gap-1.5 p-1 theme-bg-card border theme-border rounded-xl">
            {(['all', 'high', 'medium', 'unread'] as const).map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-3 py-1.5 rounded-lg text-xs font-bold capitalize transition-all ${
                  filter === f
                    ? 'bg-yellow-500 text-slate-950 shadow-md'
                    : 'theme-text-muted hover:theme-text-main'
                }`}
              >
                {f}
              </button>
            ))}
          </div>
        </div>

        {/* Alerts List */}
        <div className="space-y-4 animate-fade-in">
          {filtered.length === 0 ? (
            <div className="theme-bg-card border theme-border rounded-3xl p-12 text-center theme-text-muted">
              <CheckCircle2 size={40} className="mx-auto mb-3 text-yellow-500 opacity-60" />
              <h3 className="font-bold theme-text-main text-base">{t('feed.all_clear', lang)}</h3>
              <p className="text-xs theme-text-muted mt-1">Your inventory buffers and wholesale price parities are healthy.</p>
            </div>
          ) : (
            filtered.map((item) => {
              const isHigh = item.severity === 'high';
              const isMed = item.severity === 'medium';
              const borderClass = isHigh ? 'border-l-4 border-l-rose-500' : isMed ? 'border-l-4 border-l-amber-500' : 'border-l-4 border-l-blue-500';
              const iconBoxClass = isHigh ? 'bg-rose-500/10 text-rose-500 border-rose-500/20' : isMed ? 'bg-amber-500/10 text-amber-500 border-amber-500/20' : 'bg-blue-500/10 text-blue-500 border-blue-500/20';

              return (
                <div
                  key={item.id}
                  className={`theme-bg-card border theme-border rounded-2xl p-5 shadow-lg transition-all hover:border-yellow-500/40 flex flex-col md:flex-row md:items-start justify-between gap-5 ${borderClass} ${item.acknowledged ? 'opacity-60' : ''}`}
                >
                  <div className="flex items-start gap-4 flex-1">
                    <div className={`w-10 h-10 rounded-xl border flex items-center justify-center shrink-0 ${iconBoxClass}`}>
                      {ALERT_ICONS[item.alert_type] || <AlertTriangle size={16} />}
                    </div>

                    <div className="space-y-1 flex-1">
                      <div className="flex items-center gap-3 flex-wrap">
                        <span className={`text-[10px] font-mono font-extrabold uppercase px-2 py-0.5 rounded border ${
                          isHigh ? 'bg-rose-500/10 text-rose-500 border-rose-500/30' : 'bg-amber-500/10 text-amber-500 border-amber-500/30'
                        }`}>
                          {item.severity} PRIORITY
                        </span>

                        <span className="text-[10px] font-mono font-bold text-yellow-500 bg-yellow-500/10 px-2 py-0.5 rounded border border-yellow-500/20 flex items-center gap-1">
                          <MessageSquare size={11} /> {t('feed.whatsapp_auto', lang)}
                        </span>

                        <span className="text-[11px] font-mono theme-text-muted">
                          {new Date(item.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                      </div>

                      <h3 className="text-base font-bold theme-text-main">
                        {item.title}
                      </h3>

                      <p className="text-xs theme-text-muted leading-relaxed">
                        {item.message}
                      </p>

                      {item.recommended_action && (
                        <div className="mt-2 text-xs font-semibold text-yellow-500 bg-yellow-500/5 border border-yellow-500/15 p-2.5 rounded-xl flex items-center gap-2">
                          <ArrowRight size={14} className="shrink-0" />
                          <span>Recommended Action: {item.recommended_action}</span>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Actions Column: Voice Speaker & Resolve Button Only */}
                  <div className="flex items-center gap-2 shrink-0 self-end md:self-start">
                    <button
                      onClick={() => speakAlert(`${item.title}. ${item.message}`, item.id)}
                      className="p-2.5 rounded-xl theme-bg-input theme-text-muted hover:theme-text-main border theme-border transition-colors"
                      title="Listen to audio alert"
                    >
                      <Volume2 size={16} className={playingId === item.id ? 'text-yellow-500 animate-pulse' : ''} />
                    </button>

                    {!item.acknowledged && (
                      <button
                        onClick={() => handleAcknowledge(item.id)}
                        className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-yellow-500 hover:bg-yellow-400 text-slate-950 font-bold text-xs shadow-md transition-colors"
                      >
                        <Check size={14} /> {t('feed.resolve', lang)}
                      </button>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>
      </main>
    </div>
  );
}
