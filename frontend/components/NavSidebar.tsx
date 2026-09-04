'use client';
import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { 
  LayoutDashboard, Database, Mic, Layers, 
  Bell, BarChart2, Settings, LogOut, Zap,
  Menu, ChevronDown, Sun, Moon
} from 'lucide-react';
import { t, type Lang } from '@/lib/i18n';

interface NavSidebarProps {
  active?: string;
  lang?: Lang;
  currentLang?: Lang;
  onLangChange?: (l: Lang) => void;
}

const NAV_ITEMS = [
  { id: 'home',       href: '/home',             icon: LayoutDashboard, key: 'nav.home',       label: 'Dashboard' },
  { id: 'datasync',   href: '/data-sync',        icon: Database,        key: 'nav.datasync',   label: 'Data Sync' },
  { id: 'talking',    href: '/talking-space',    icon: Mic,             key: 'nav.talking',    label: 'Talking Space' },
  { id: 'sandbox',    href: '/decision-sandbox', icon: Layers,          key: 'nav.sandbox',    label: 'Decision Sandbox' },
  { id: 'actionfeed', href: '/action-feed',      icon: Bell,            key: 'nav.actionfeed', label: 'Action Feed', badge: '3' },
  { id: 'reports',    href: '/reports',          icon: BarChart2,       key: 'nav.reports',    label: 'Reports' },
  { id: 'settings',   href: '/settings',         icon: Settings,        key: 'nav.settings',   label: 'Settings' },
];

export default function NavSidebar({ active, lang = 'en', currentLang }: NavSidebarProps) {
  const router = useRouter();
  const pathname = usePathname();
  const effectiveLang = currentLang || lang;
  
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [theme, setTheme] = useState<'dark' | 'light'>('dark');

  useEffect(() => {
    const savedTheme = localStorage.getItem('bizpanion_theme') as 'dark' | 'light';
    if (savedTheme) {
      setTheme(savedTheme);
      document.documentElement.setAttribute('data-theme', savedTheme);
    } else {
      document.documentElement.setAttribute('data-theme', 'dark');
    }
  }, []);

  function toggleTheme() {
    const nextTheme = theme === 'dark' ? 'light' : 'dark';
    setTheme(nextTheme);
    localStorage.setItem('bizpanion_theme', nextTheme);
    document.documentElement.setAttribute('data-theme', nextTheme);
  }

  function handleLogout() {
    localStorage.clear();
    router.push('/onboarding');
  }

  const activeItem = NAV_ITEMS.find(i => (active ? active === i.id : pathname === i.href)) || NAV_ITEMS[0];
  const translatedActiveLabel = t(activeItem.key, effectiveLang);
  const displaySpaceName = translatedActiveLabel.toLowerCase().includes('space') || translatedActiveLabel.toLowerCase().includes('स्पेस') || translatedActiveLabel.toLowerCase().includes('இடம்') || translatedActiveLabel.toLowerCase().includes('స్పేస్') || translatedActiveLabel.toLowerCase().includes('ಸ್ಪೇಸ್')
    ? translatedActiveLabel
    : `${translatedActiveLabel} Space`;

  return (
    <aside className="w-64 fixed left-0 top-0 bottom-0 theme-bg-sidebar border-r theme-border z-50 flex flex-col justify-between p-4 select-none shadow-2xl transition-colors">
      {/* Top Section */}
      <div>
        {/* Brand Header */}
        <div className="pb-4 pt-1 px-1 border-b theme-border mb-3 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-yellow-500 to-amber-400 flex items-center justify-center shadow-lg shadow-yellow-500/20 text-slate-950 font-black text-xl">
              B
            </div>
            <div>
              <span className="font-extrabold text-lg tracking-tight theme-text-main block leading-none">
                Bizpanion
              </span>
              <span className="text-[10px] font-mono font-bold tracking-widest text-yellow-500 uppercase mt-1 block">
                Autonomous Cockpit
              </span>
            </div>
          </div>

          {/* Theme Toggle Button */}
          <button
            onClick={toggleTheme}
            className="p-2 rounded-xl theme-bg-card hover:bg-yellow-500/10 theme-text-muted hover:text-yellow-500 transition-colors border theme-border"
            title={`Switch to ${theme === 'dark' ? 'Light' : 'Dark'} Mode`}
          >
            {theme === 'dark' ? <Sun size={15} /> : <Moon size={15} />}
          </button>
        </div>

        {/* 3-Line Hamburger Dropdown Space Selector */}
        <div className="relative mb-4">
          <button
            onClick={() => setIsDropdownOpen(!isDropdownOpen)}
            className="w-full flex items-center justify-between px-3 py-2.5 rounded-xl theme-bg-card border theme-border theme-text-main text-xs font-bold shadow-sm hover:border-yellow-500/50 transition-all"
          >
            <div className="flex items-center gap-2">
              <Menu size={16} className="text-yellow-500 shrink-0" />
              <span className="truncate">{displaySpaceName}</span>
            </div>
            <ChevronDown size={14} className={`transition-transform duration-200 ${isDropdownOpen ? 'rotate-180' : ''}`} />
          </button>

          {/* Dropdown Menu */}
          {isDropdownOpen && (
            <div className="absolute left-0 right-0 top-12 theme-bg-card border theme-border rounded-xl shadow-2xl p-1.5 z-50 space-y-1 animate-fade-in">
              {NAV_ITEMS.map((item) => {
                const Icon = item.icon;
                const isSelected = active ? active === item.id : pathname === item.href;
                const itemTranslated = t(item.key, effectiveLang);
                return (
                  <button
                    key={item.id}
                    onClick={() => {
                      setIsDropdownOpen(false);
                      router.push(item.href);
                    }}
                    className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-xs font-medium transition-colors ${
                      isSelected
                        ? 'bg-yellow-500 text-slate-950 font-bold'
                        : 'theme-text-muted hover:theme-text-main hover:bg-yellow-500/10'
                    }`}
                  >
                    <div className="flex items-center gap-2.5">
                      <Icon size={14} />
                      <span>{itemTranslated}</span>
                    </div>
                    {item.badge && (
                      <span className="text-[9px] font-bold bg-rose-500/20 text-rose-400 px-1.5 py-0.5 rounded-full">
                        {item.badge}
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* Active Space Details Card */}
        <div className="theme-bg-card border theme-border rounded-2xl p-4 space-y-3 shadow-md">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-mono font-bold text-yellow-500 bg-yellow-500/10 px-2 py-0.5 rounded uppercase">
              ACTIVE SPACE
            </span>
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          </div>
          <h4 className="font-extrabold theme-text-main text-sm">
            {translatedActiveLabel} Cockpit
          </h4>
          <p className="text-[11px] theme-text-muted leading-relaxed">
            Use the top menu dropdown above to switch between Dashboard, Data Sync, Voice Copilot, Decision Sandbox, Action Feed, Reports, and Settings.
          </p>
        </div>
      </div>

      {/* Bottom Section */}
      <div className="pt-3 border-t theme-border space-y-2.5">
        <div className="theme-bg-card border theme-border rounded-xl p-2.5 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-yellow-500 animate-pulse" />
            <span className="text-[11px] font-medium theme-text-main">Tally Port 9000</span>
          </div>
          <span className="text-[10px] font-mono text-yellow-500 bg-yellow-500/10 px-1.5 py-0.5 rounded font-bold">
            SYNCED
          </span>
        </div>

        <button
          id="nav-logout"
          onClick={handleLogout}
          className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-medium theme-text-muted hover:text-rose-500 hover:bg-rose-500/10 transition-colors"
        >
          <LogOut size={15} />
          <span>{t('nav.logout', effectiveLang)}</span>
        </button>

        <div className="px-1 text-[10px] theme-text-muted font-mono flex items-center gap-1">
          <Zap size={11} className="text-yellow-500" /> Powered by <span className="text-yellow-500 font-semibold">Featherless.ai</span>
        </div>
      </div>
    </aside>
  );
}
