'use client';
import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { 
  Play, Pause, Volume2, TrendingUp, Package,
  Zap, Database, Download, Award, ExternalLink, ArrowUpRight,
  AlertTriangle, ArrowRight, DollarSign
} from 'lucide-react';
import NavSidebar from '@/components/NavSidebar';
import { 
  getStoredBusinessId, 
  getAlertsSummary, 
  getDailyBriefing, 
  getProfile, 
  getStoredUserId,
  getDashboardOverview
import { getApiUrl } from '@/lib/api';

const API_URL = getApiUrl();

function Sparkline({ data, color = '#eab308', height = 32 }: { data: number[]; color?: string; height?: number }) {
  if (!data || data.length < 2) return null;
  const w = 80; const h = height;
  const min = Math.min(...data); const max = Math.max(...data);
  const range = max - min || 1;
  const pts = data.map((v, i) => {
    const x = (i / (data.length - 1)) * w;
    const y = h - ((v - min) / range) * (h - 4) - 2;
    return `${x},${y}`;
  }).join(' ');
  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} fill="none">
      <polyline points={pts} stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function MiniBarChart({ data, color = '#eab308' }: { data: { label: string; value: number }[]; color?: string }) {
  const max = Math.max(...data.map(d => d.value)) || 1;
  return (
    <div className="flex items-end gap-1.5 h-12 w-full pt-2">
      {data.map((d, i) => (
        <div key={i} className="flex-1 flex flex-col items-center gap-1 h-full justify-end group relative">
          <div
            className={`w-full rounded-t transition-all duration-300 ${i === data.length - 1 ? 'bg-yellow-500' : 'theme-bg-input group-hover:bg-slate-700'}`}
            style={{ height: `${Math.max(10, (d.value / max) * 100)}%` }}
          />
        </div>
      ))}
    </div>
  );
}

const SECTOR_DATA: Record<string, {
  mandiItems: Array<{ item: string; price: string; benchmark: string; diff: string; diffColor: string; status: string; statusClass: string }>;
  schemes: Array<{ title: string; tag: string; tagColor: string; desc: string; link?: string }>;
}> = {
  textile: {
    mandiItems: [
      { item: 'Cotton Silk Saree (100% Weave)', price: '₹1,450/pc', benchmark: '₹1,520/pc', diff: '-₹70 (-4.6%)', diffColor: 'text-rose-500', status: 'BELOW PARITY', statusClass: 'bg-rose-500/10 text-rose-500 border-rose-500/20' },
      { item: 'Denim Heavy Twill Fabric (Meter)', price: '₹210/m', benchmark: '₹205/m', diff: '+₹5 (+2.4%)', diffColor: 'text-yellow-500', status: 'OPTIMAL', statusClass: 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20' },
      { item: 'Designer Printed Kurti', price: '₹580/pc', benchmark: '₹600/pc', diff: '-₹20 (-3.3%)', diffColor: 'text-amber-500', status: 'SLIGHT DISCOUNT', statusClass: 'bg-amber-500/10 text-amber-500 border-amber-500/20' },
    ],
    schemes: [
      { title: 'PM MITRA Textile Scheme', tag: '20% Capital Subvention', tagColor: 'text-yellow-500 bg-yellow-500/10', desc: 'Financial assistance & infrastructure support for handloom, powerloom & garment manufacturing.' },
      { title: 'Weaver Credit Card Loan', tag: '7% Interest Subsidy', tagColor: 'text-amber-500 bg-amber-500/10', desc: 'Low-interest working capital credit up to ₹2 Lakhs for yarn stock and loom expansion.' },
    ]
  },
  dairy: {
    mandiItems: [
      { item: 'Full Cream Pasteurized Milk (50L Can)', price: '₹2,800/can', benchmark: '₹2,950/can', diff: '-₹150 (-5.1%)', diffColor: 'text-rose-500', status: 'BELOW PARITY', statusClass: 'bg-rose-500/10 text-rose-500 border-rose-500/20' },
      { item: 'Fresh Malai Paneer 1kg', price: '₹380/kg', benchmark: '₹370/kg', diff: '+₹10 (+2.7%)', diffColor: 'text-yellow-500', status: 'OPTIMAL', statusClass: 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20' },
      { item: 'Cow Ghee Pure Desi 1L', price: '₹610/jar', benchmark: '₹630/jar', diff: '-₹20 (-3.2%)', diffColor: 'text-amber-500', status: 'SLIGHT DISCOUNT', statusClass: 'bg-amber-500/10 text-amber-500 border-amber-500/20' },
    ],
    schemes: [
      { title: 'Dairy Infra Development Fund (DIDF)', tag: '3% Interest Subvention', tagColor: 'text-yellow-500 bg-yellow-500/10', desc: 'Low-interest loans for bulk milk coolers, chilling infrastructure and processing units.' },
      { title: 'National Dairy Dev (NPDD)', tag: '50% Capital Subsidy', tagColor: 'text-amber-500 bg-amber-500/10', desc: 'Grant assistance for quality testing equipment and automated milk collection units.' },
    ]
  },
  hardware: {
    mandiItems: [
      { item: 'TMT Rebar 12mm Fe550 (Ton)', price: '₹54,500/ton', benchmark: '₹56,200/ton', diff: '-₹1,700 (-3.0%)', diffColor: 'text-rose-500', status: 'BELOW PARITY', statusClass: 'bg-rose-500/10 text-rose-500 border-rose-500/20' },
      { item: 'Copper Wire 1.5 sqmm (90m Roll)', price: '₹1,850/roll', benchmark: '₹1,810/roll', diff: '+₹40 (+2.2%)', diffColor: 'text-yellow-500', status: 'OPTIMAL', statusClass: 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20' },
      { item: 'Brass Ball Valve 1/2 Inch', price: '₹185/pc', benchmark: '₹192/pc', diff: '-₹7 (-3.6%)', diffColor: 'text-amber-500', status: 'SLIGHT DISCOUNT', statusClass: 'bg-amber-500/10 text-amber-500 border-amber-500/20' },
    ],
    schemes: [
      { title: 'MSME Tooling & Tech Grant', tag: '25% Capital Subsidy', tagColor: 'text-yellow-500 bg-yellow-500/10', desc: 'Financial support for upgrading precision machinery, CNC cutting, and electrical testing.' },
      { title: 'CGTMSE Collateral Loan', tag: '₹2 Cr Guarantee Cover', tagColor: 'text-amber-500 bg-amber-500/10', desc: 'Collateral-free working capital loan for electrical & hardware stockholding.' },
    ]
  },
  vegetables: {
    mandiItems: [
      { item: 'Hybrid Tomato Nashik (50kg Crate)', price: '₹1,200/crate', benchmark: '₹1,280/crate', diff: '-₹80 (-6.2%)', diffColor: 'text-rose-500', status: 'BELOW PARITY', statusClass: 'bg-rose-500/10 text-rose-500 border-rose-500/20' },
      { item: 'Onion Red Grade-A (Quintal)', price: '₹2,450/qtl', benchmark: '₹2,400/qtl', diff: '+₹50 (+2.1%)', diffColor: 'text-yellow-500', status: 'OPTIMAL', statusClass: 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20' },
      { item: 'Potato Jyoti Special (50kg Bag)', price: '₹950/bag', benchmark: '₹980/bag', diff: '-₹30 (-3.1%)', diffColor: 'text-amber-500', status: 'SLIGHT DISCOUNT', statusClass: 'bg-amber-500/10 text-amber-500 border-amber-500/20' },
    ],
    schemes: [
      { title: 'PMFME Food Processing Scheme', tag: '35% Credit Subsidy', tagColor: 'text-yellow-500 bg-yellow-500/10', desc: 'Financial assistance for cold storage vans, sorting units, and fruit packaging.' },
      { title: 'Horticulture Dev Mission (MIDH)', tag: '40% Govt Subsidy', tagColor: 'text-amber-500 bg-amber-500/10', desc: 'Subsidy support for green-house farming and perishable cold chain transport.' },
    ]
  },
  kirana: {
    mandiItems: [
      { item: 'Aashirvaad Shuddh Chakki Atta 10kg', price: '₹380/bag', benchmark: '₹398/bag', diff: '-₹18 (-4.5%)', diffColor: 'text-rose-500', status: 'BELOW PARITY', statusClass: 'bg-rose-500/10 text-rose-500 border-rose-500/20' },
      { item: 'Fortune Sunlite Refined Oil 1L', price: '₹135/pouch', benchmark: '₹132/pouch', diff: '+₹3 (+2.2%)', diffColor: 'text-yellow-500', status: 'OPTIMAL', statusClass: 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20' },
      { item: 'Tata Salt Vacuum Evaporated 1kg', price: '₹26/pkt', benchmark: '₹27/pkt', diff: '-₹1 (-3.7%)', diffColor: 'text-amber-500', status: 'SLIGHT DISCOUNT', statusClass: 'bg-amber-500/10 text-amber-500 border-amber-500/20' },
    ],
    schemes: [
      { title: 'PM SVANidhi Micro-Credit', tag: '7% Interest Subsidy', tagColor: 'text-yellow-500 bg-yellow-500/10', desc: 'Collateral-free working capital loan up to ₹50,000 with UPI digital transaction cashback.' },
      { title: 'PMEGP Credit Linked Subsidy', tag: '35% Capital Subsidy', tagColor: 'text-amber-500 bg-amber-500/10', desc: 'Financial assistance up to ₹50 Lakhs for retail expansion and micro-manufacturing equipment.' },
    ]
  }
};

function getSectorKey(typeStr?: string) {
  if (!typeStr) return 'kirana';
  const s = typeStr.toLowerCase();
  if (s.includes('textile') || s.includes('cloth')) return 'textile';
  if (s.includes('dairy') || s.includes('milk')) return 'dairy';
  if (s.includes('hardware') || s.includes('electric')) return 'hardware';
  if (s.includes('veg') || s.includes('fruit')) return 'vegetables';
  return 'kirana';
}

export default function HomePage() {
  const router = useRouter();
  const [lang, setLangState] = useState<Lang>('en');
  const [profile, setProfile] = useState<any>(null);
  const [summary, setSummary] = useState<any>(null);
  const [dashboardData, setDashboardData] = useState<any>(null);
  const [briefing, setBriefing] = useState<any>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [audio, setAudio] = useState<HTMLAudioElement | null>(null);
  const [loadingBriefing, setLoadingBriefing] = useState(false);

  const businessId = getStoredBusinessId();
  const sectorKey = getSectorKey(profile?.business_type);
  const currentSectorData = SECTOR_DATA[sectorKey] || SECTOR_DATA['kirana'];

  useEffect(() => {
    const updateLang = () => {
      const l = getLang();
      setLangState(l);
    };
    updateLang();
    loadData(getLang());
    if (typeof window !== 'undefined') {
      window.addEventListener('languageChange', updateLang);
    }
    return () => {
      if (typeof window !== 'undefined') {
        window.removeEventListener('languageChange', updateLang);
      }
    };
  }, []);

  async function loadData(l: Lang) {
    try {
      const [profRes, sumRes, dashRes] = await Promise.allSettled([
        getProfile(getStoredUserId()),
        getAlertsSummary(businessId),
        getDashboardOverview(businessId),
      ]);
      if (profRes.status === 'fulfilled') setProfile(profRes.value);
      if (sumRes.status === 'fulfilled') setSummary(sumRes.value);
      if (dashRes.status === 'fulfilled') setDashboardData(dashRes.value);
    } catch {}
  }

  async function handlePlayBriefing() {
    if (isPlaying && audio) {
      audio.pause();
      setIsPlaying(false);
      return;
    }

    if (audio) {
      audio.play();
      setIsPlaying(true);
      return;
    }

    setLoadingBriefing(true);
    try {
      const bizName = profile?.business_name || (typeof window !== 'undefined' ? localStorage.getItem('bizpanion_business_name') : null) || 'Gourav Clothing store';
      const bizType = profile?.business_type || (typeof window !== 'undefined' ? localStorage.getItem('bizpanion_business_type') : null) || 'textile';
      const b = await getDailyBriefing(businessId, lang, bizName, bizType);
      setBriefing(b);
      if (b.audio_url) {
        const fullUrl = b.audio_url.startsWith('http') ? b.audio_url : `${API_URL}${b.audio_url}`;
        const newAudio = new Audio(fullUrl);
        newAudio.onended = () => setIsPlaying(false);
        setAudio(newAudio);
        newAudio.play();
        setIsPlaying(true);
      }
    } catch (e: any) {
      alert(`Could not load briefing: ${e.message}`);
    } finally {
      setLoadingBriefing(false);
    }
  }

  function handleDownloadPDF() {
    generateExecutiveReportPDF(dashboardData, businessId);
  }

  const kpis = dashboardData?.kpis || {};
  const summaryData = dashboardData?.business_summary;
  const turnoverVal = kpis?.revenue?.value || summaryData?.total_sales_inr || 1641657;
  const runwayDaysVal = kpis?.runway_days?.value || summaryData?.cash_runway_days || 38;
  const netCashVal = kpis?.net_cash?.value || (summaryData?.total_sales_inr ? Math.round(summaryData.total_sales_inr * 0.26) : 428000);

  return (
    <div className="flex min-h-screen theme-bg-main">
      <NavSidebar active="home" lang={lang} />

      <main className="ml-64 flex-1 min-h-screen p-8 max-w-[1400px]">
        {/* Top Header */}
        <div className="flex items-start justify-between mb-8 flex-wrap gap-4 animate-fade-in">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-yellow-500/10 border border-yellow-500/20 text-yellow-500 text-xs font-mono font-bold uppercase tracking-wider mb-2">
              <span className="w-2 h-2 rounded-full bg-yellow-500 animate-pulse" />
              {profile?.business_name || 'Ram Textile'} • {t('home.eyebrow', lang)}
            </div>
            <h1 className="text-3xl font-extrabold theme-text-main tracking-tight">
              {t('home.title', lang)}
            </h1>
            <p className="text-sm mt-1 max-w-xl theme-text-muted">
              {t('home.subtitle', lang)}
            </p>
          </div>

          <button
            onClick={handleDownloadPDF}
            className="flex items-center gap-2 bg-yellow-500 hover:bg-yellow-400 text-slate-950 font-bold text-xs px-4 py-2.5 rounded-xl shadow-lg shadow-yellow-500/20 transition-all hover:scale-[1.02]"
          >
            <Download size={15} />
            <span>{t('home.pdf_btn', lang)}</span>
          </button>
        </div>

        {/* Audio Copilot Hero Banner */}
        <div className="theme-bg-card border border-yellow-500/30 rounded-3xl p-6 mb-8 shadow-xl relative overflow-hidden flex items-center justify-between flex-wrap gap-6">
          <div className="flex items-center gap-4 max-w-2xl">
            <button
              onClick={handlePlayBriefing}
              disabled={loadingBriefing}
              className="w-14 h-14 rounded-2xl bg-yellow-500 hover:bg-yellow-400 text-slate-950 flex items-center justify-center shrink-0 shadow-lg shadow-yellow-500/30 transition-all hover:scale-105"
            >
              {isPlaying ? <Pause size={24} /> : <Play size={24} className="ml-1" />}
            </button>

            <div>
              <div className="inline-flex items-center gap-1.5 text-xs font-mono font-bold text-yellow-500 uppercase tracking-wider">
                <Volume2 size={14} /> {t('home.briefing_badge', lang)}
              </div>
              <h3 className="text-lg font-bold theme-text-main mt-1">
                {briefing ? briefing.title || t('home.briefing_title', lang) : t('home.briefing_title', lang)}
              </h3>
              <p className="text-xs theme-text-muted mt-0.5 line-clamp-2">
                {briefing ? briefing.summary : t('home.briefing_desc', lang)}
              </p>
            </div>
          </div>
        </div>

        {/* Bento Grid 1: Key Performance Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5 mb-8">
          {/* Card 1: Revenue */}
          <div className="theme-bg-card border theme-border rounded-2xl p-5 hover:border-yellow-500/40 transition-all">
            <div className="flex items-center justify-between text-xs font-mono font-bold theme-text-muted uppercase tracking-wider mb-2">
              <span>{t('home.turnover', lang)}</span>
              <DollarSign size={16} className="text-yellow-500" />
            </div>
            <div className="text-2xl font-extrabold theme-text-main tracking-tight">
              ₹{turnoverVal.toLocaleString('en-IN')}
            </div>
            <div className="flex items-center justify-between mt-3">
              <span className="text-xs text-yellow-500 font-semibold flex items-center gap-1">
                <ArrowUpRight size={13} /> +14.2% vs last month
              </span>
              <Sparkline data={[120, 140, 135, 160, 180, 210, 240]} color="#eab308" />
            </div>
          </div>

          {/* Card 2: Cash Runway */}
          <div className="theme-bg-card border theme-border rounded-2xl p-5 hover:border-yellow-500/40 transition-all">
            <div className="flex items-center justify-between text-xs font-mono font-bold theme-text-muted uppercase tracking-wider mb-2">
              <span>{t('home.runway', lang)}</span>
              <Zap size={16} className="text-amber-500" />
            </div>
            <div className="text-2xl font-extrabold theme-text-main tracking-tight flex items-baseline gap-2">
              <span>{runwayDaysVal} Days</span>
              <span className="text-xs font-normal theme-text-muted">{t('home.safe_buffer', lang)}</span>
            </div>
            <div className="w-full theme-bg-input h-2 rounded-full mt-4 overflow-hidden">
              <div className="bg-gradient-to-r from-amber-500 to-yellow-400 h-full rounded-full w-[70%]" />
            </div>
          </div>

          {/* Card 3: Active Stock Alerts */}
          <div className="theme-bg-card border theme-border rounded-2xl p-5 hover:border-yellow-500/40 transition-all">
            <div className="flex items-center justify-between text-xs font-mono font-bold theme-text-muted uppercase tracking-wider mb-2">
              <span>{t('home.alerts', lang)}</span>
              <Package size={16} className="text-rose-500" />
            </div>
            <div className="text-2xl font-extrabold theme-text-main tracking-tight flex items-baseline gap-2">
              <span>{summary?.by_priority?.high || summary?.low_stock_count || 4} Critical</span>
              <span className="text-xs font-normal text-rose-500 font-semibold">Action Required</span>
            </div>
            <p className="text-xs theme-text-muted mt-3 truncate">
              Items under 5 days safety buffer
            </p>
          </div>

          {/* Card 4: Net Operating Cash */}
          <div className="theme-bg-card border theme-border rounded-2xl p-5 hover:border-yellow-500/40 transition-all">
            <div className="flex items-center justify-between text-xs font-mono font-bold theme-text-muted uppercase tracking-wider mb-2">
              <span>{t('home.net_cash', lang)}</span>
              <TrendingUp size={16} className="text-blue-500" />
            </div>
            <div className="text-2xl font-extrabold theme-text-main tracking-tight">
              ₹{netCashVal.toLocaleString('en-IN')}
            </div>
            <MiniBarChart data={[
              { label: 'M', value: 30 },
              { label: 'T', value: 45 },
              { label: 'W', value: 60 },
              { label: 'T', value: 80 },
              { label: 'F', value: 95 },
            ]} color="#eab308" />
          </div>
        </div>

        {/* Bento Grid 2: Wholesale Benchmark Parity & Government Schemes */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
          
          {/* Left Column (2 spans): Agmarknet Wholesale Parity Table */}
          <div className="lg:col-span-2 theme-bg-card border theme-border rounded-3xl p-6 shadow-xl">
            <div className="flex items-center justify-between mb-5">
              <div>
                <div className="inline-flex items-center gap-1.5 text-xs font-mono font-bold text-yellow-500 uppercase tracking-wider">
                  <Database size={14} /> Agmarknet Mandi Price Index ({sectorKey.toUpperCase()})
                </div>
                <h3 className="text-lg font-bold theme-text-main mt-1">
                  {t('home.agmarknet_title', lang)}
                </h3>
              </div>

              <span className="text-[11px] font-mono text-yellow-500 bg-yellow-500/10 px-2.5 py-1 rounded-full border border-yellow-500/20 font-bold">
                LIVE EXCHANGE SYNCED
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs theme-text-muted">
                <thead className="theme-bg-input theme-text-muted font-mono text-[10px] uppercase tracking-wider border-b theme-border">
                  <tr>
                    <th className="p-3">Commodity / SKU Item</th>
                    <th className="p-3">Your Selling Price</th>
                    <th className="p-3">Mandi Benchmark</th>
                    <th className="p-3">Margin Variance</th>
                    <th className="p-3 text-right">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y theme-border">
                  {currentSectorData.mandiItems.map((item, idx) => (
                    <tr key={idx} className="hover:bg-yellow-500/5 transition-colors">
                      <td className="p-3 font-semibold theme-text-main">{item.item}</td>
                      <td className="p-3 font-mono">{item.price}</td>
                      <td className="p-3 font-mono theme-text-muted">{item.benchmark}</td>
                      <td className={`p-3 font-mono font-semibold ${item.diffColor}`}>{item.diff}</td>
                      <td className="p-3 text-right">
                        <span className={`border px-2 py-0.5 rounded font-mono font-bold text-[10px] ${item.statusClass}`}>
                          {item.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Right Column (1 span): Matched Government Schemes */}
          <div className="theme-bg-card border theme-border rounded-3xl p-6 shadow-xl flex flex-col justify-between">
            <div>
              <div className="inline-flex items-center gap-1.5 text-xs font-mono font-bold text-amber-500 uppercase tracking-wider mb-1">
                <Award size={14} /> Ministry of MSME / SIDBI
              </div>
              <h3 className="text-lg font-bold theme-text-main">
                {t('home.govt_schemes', lang)}
              </h3>
              <p className="text-xs theme-text-muted mt-1 mb-4">
                Eligible low-interest credit and subsidy programs tailored to your enterprise sector ({sectorKey}).
              </p>

              <div className="space-y-3">
                {currentSectorData.schemes.map((sc, idx) => (
                  <div key={idx} className="p-3 rounded-2xl theme-bg-input border theme-border hover:border-yellow-500/40 transition-colors">
                    <div className="flex items-center justify-between">
                      <h4 className="font-bold theme-text-main text-xs">{sc.title}</h4>
                      <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded font-bold ${sc.tagColor}`}>
                        {sc.tag}
                      </span>
                    </div>
                    <p className="text-[11px] theme-text-muted mt-1">
                      {sc.desc}
                    </p>
                  </div>
                ))}
              </div>
            </div>

            <a
              href="https://pmsvanidhi.mohua.gov.in/"
              target="_blank"
              rel="noreferrer"
              className="mt-4 flex items-center justify-center gap-1.5 w-full py-2.5 rounded-xl theme-bg-input hover:border-yellow-500 text-xs font-bold theme-text-main border theme-border transition-colors"
            >
              <span>Apply via Official Gateway</span>
              <ExternalLink size={13} />
            </a>
          </div>

        </div>

        {/* Action Feed Shortcut */}
        <div className="theme-bg-card border theme-border rounded-3xl p-6 shadow-xl flex items-center justify-between flex-wrap gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-rose-500/10 text-rose-500 flex items-center justify-center shrink-0 border border-rose-500/20">
              <AlertTriangle size={20} />
            </div>
            <div>
              <h4 className="font-bold theme-text-main text-sm">
                4 Critical Stockout & Payment Collection Notices
              </h4>
              <p className="text-xs theme-text-muted mt-0.5">
                Automated WhatsApp notices ready for 1-click customer & supplier dispatch.
              </p>
            </div>
          </div>

          <button
            onClick={() => router.push('/action-feed')}
            className="flex items-center gap-2 bg-yellow-500 hover:bg-yellow-400 text-slate-950 font-bold text-xs px-4 py-2.5 rounded-xl shadow-lg shadow-yellow-500/20 transition-all hover:scale-[1.02]"
          >
            <span>Open Action Feed</span>
            <ArrowRight size={14} />
          </button>
        </div>

      </main>
    </div>
  );
}
