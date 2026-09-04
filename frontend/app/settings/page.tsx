'use client';
import React, { useState, useEffect } from 'react';
import { Save, Check, Settings, User, Globe, Sun, Moon } from 'lucide-react';
import NavSidebar from '@/components/NavSidebar';
import { getStoredUserId, getProfile, updateProfile } from '@/lib/api';
import { getLang, setLang, LANGUAGE_NAMES, t, type Lang } from '@/lib/i18n';

const BUSINESS_TYPES = ['kirana_shop','grocery_store','dairy_farmer','textile','hardware_electrical','vegetable_vendor','other'];
const LANGUAGES = ['en','hi','ta','te','kn'];

export default function SettingsPage() {
  const [lang, setLangState] = useState<Lang>(getLang());
  const [profile, setProfile] = useState<any>(null);
  const [form, setForm] = useState<any>({});
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [theme, setTheme] = useState<'dark' | 'light'>('dark');
  const userId = getStoredUserId();

  useEffect(() => {
    const activeLang = getLang();
    setLangState(activeLang);
    const savedTheme = (localStorage.getItem('bizpanion_theme') as 'dark' | 'light') || 'dark';
    setTheme(savedTheme);

    const localBizName = typeof window !== 'undefined' ? (localStorage.getItem('bizpanion_business_name') || 'Fresh Greens') : 'Fresh Greens';
    const localWhatsapp = typeof window !== 'undefined' ? (localStorage.getItem('bizpanion_whatsapp') || '9518948695') : '9518948695';

    getProfile(userId).then(p => {
      setProfile(p);
      setForm({
        business_name: p?.business_name || localBizName,
        whatsapp_number: p?.whatsapp_number || localWhatsapp,
        business_type: p?.business_type || 'kirana_shop',
        region: p?.region || 'Maharashtra',
        alert_sensitivity: p?.alert_sensitivity || 'high',
        ...(p || {}),
        language: activeLang || p?.language || 'en',
      });
    }).catch(() => {
      setForm({
        business_name: localBizName,
        whatsapp_number: localWhatsapp,
        business_type: 'kirana_shop',
        region: 'Maharashtra',
        language: activeLang || 'en',
        alert_sensitivity: 'high',
      });
    });
  }, [userId]);

  const update = (k: string, v: string) => setForm((f: any) => ({ ...f, [k]: v }));

  function toggleTheme(nextTheme: 'dark' | 'light') {
    setTheme(nextTheme);
    localStorage.setItem('bizpanion_theme', nextTheme);
    document.documentElement.setAttribute('data-theme', nextTheme);
  }

  async function handleLanguageSelect(selectedLang: string) {
    const l = selectedLang as Lang;
    update('language', l);
    setLangState(l);
    setLang(l);
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new Event('languageChange'));
    }
    if (userId) {
      updateProfile(userId, { language: l }).catch(console.error);
    }
  }

  async function handleSave() {
    setSaving(true);
    try {
      if (form.business_name) localStorage.setItem('bizpanion_business_name', form.business_name);
      if (form.whatsapp_number) localStorage.setItem('bizpanion_whatsapp', form.whatsapp_number);
      if (form.language) {
        setLangState(form.language as Lang);
        setLang(form.language as Lang);
        if (typeof window !== 'undefined') {
          window.dispatchEvent(new Event('languageChange'));
        }
      }
      await updateProfile(userId, {
        business_name: form.business_name || 'Fresh Greens',
        business_type: form.business_type || 'kirana_shop',
        region: form.region || 'Maharashtra',
        language: form.language || 'en',
        whatsapp_number: form.whatsapp_number || '9518948695',
        alert_sensitivity: form.alert_sensitivity || 'high',
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (e) { console.error(e); }
    finally { setSaving(false); }
  }

  return (
    <div className="flex min-h-screen theme-bg-main">
      <NavSidebar active="settings" lang={lang} />

      <main className="ml-64 flex-1 min-h-screen p-8 max-w-[1200px]">
        {/* Header */}
        {/* Header */}
        <div className="flex items-start justify-between mb-8 flex-wrap gap-4 animate-fade-in">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-yellow-500/10 border border-yellow-500/20 text-yellow-500 text-xs font-mono font-bold uppercase tracking-wider mb-2">
              <Settings size={13} /> {t('nav.settings', lang)}
            </div>
            <h1 className="text-3xl font-extrabold theme-text-main tracking-tight">
              {t('settings.title', lang)}
            </h1>
            <p className="text-xs theme-text-muted mt-1 max-w-xl">
              {t('settings.subtitle', lang)}
            </p>
          </div>

          <button
            onClick={handleSave}
            disabled={saving}
            className="flex items-center gap-2 bg-yellow-500 hover:bg-yellow-400 text-slate-950 font-bold text-xs px-5 py-2.5 rounded-xl shadow-lg shadow-yellow-500/20 transition-all hover:scale-[1.02]"
          >
            {saved ? <Check size={16} /> : <Save size={16} />}
            <span>{saving ? '...' : saved ? t('settings.saved_btn', lang) : t('settings.save_btn', lang)}</span>
          </button>
        </div>

        {/* Settings Cards */}
        <div className="space-y-6 animate-fade-in">
          {/* Card 1: Theme & Display Preferences */}
          <div className="theme-bg-card border theme-border rounded-3xl p-6 shadow-xl">
            <h3 className="text-base font-bold theme-text-main mb-1 flex items-center gap-2">
              <Sun size={18} className="text-yellow-500" /> {t('settings.visual_theme', lang)}
            </h3>
            <p className="text-xs theme-text-muted mb-4">
              {t('settings.visual_theme_desc', lang)}
            </p>

            <div className="flex gap-4">
              <button
                onClick={() => toggleTheme('dark')}
                className={`flex-1 p-4 rounded-2xl border transition-all text-left flex items-center justify-between ${
                  theme === 'dark'
                    ? 'bg-slate-900 border-yellow-500 text-white shadow-md ring-1 ring-yellow-500'
                    : 'theme-bg-input theme-border theme-text-muted hover:theme-text-main'
                }`}
              >
                <div className="flex items-center gap-3">
                  <Moon size={20} className="text-yellow-500" />
                  <div>
                    <h4 className="font-bold text-xs">{t('settings.dark_mode', lang)}</h4>
                    <p className="text-[11px] text-slate-400 mt-0.5">Obsidian Dark Fintech UI</p>
                  </div>
                </div>
                {theme === 'dark' && <Check size={16} className="text-yellow-500" />}
              </button>

              <button
                onClick={() => toggleTheme('light')}
                className={`flex-1 p-4 rounded-2xl border transition-all text-left flex items-center justify-between ${
                  theme === 'light'
                    ? 'bg-white border-yellow-500 text-slate-950 shadow-md ring-1 ring-yellow-500'
                    : 'theme-bg-input theme-border theme-text-muted hover:theme-text-main'
                }`}
              >
                <div className="flex items-center gap-3">
                  <Sun size={20} className="text-yellow-500" />
                  <div>
                    <h4 className="font-bold text-xs">{t('settings.light_mode', lang)}</h4>
                    <p className="text-[11px] text-slate-600 mt-0.5">Clean Editorial Light UI</p>
                  </div>
                </div>
                {theme === 'light' && <Check size={16} className="text-yellow-500" />}
              </button>
            </div>
          </div>

          {/* Card 2: Language & Dialect Selection */}
          <div className="theme-bg-card border theme-border rounded-3xl p-6 shadow-xl">
            <h3 className="text-base font-bold theme-text-main mb-1 flex items-center gap-2">
              <Globe size={18} className="text-yellow-500" /> {t('settings.lang_header', lang)}
            </h3>
            <p className="text-xs theme-text-muted mb-4">
              {t('settings.lang_desc', lang)}
            </p>

            <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
              {LANGUAGES.map((lCode) => {
                const isSelected = form.language === lCode;
                return (
                  <button
                    key={lCode}
                    onClick={() => handleLanguageSelect(lCode)}
                    className={`p-3 rounded-2xl border text-center font-bold text-xs transition-all ${
                      isSelected
                        ? 'bg-yellow-500 text-slate-950 shadow-md border-yellow-500'
                        : 'theme-bg-input theme-border theme-text-muted hover:theme-text-main'
                    }`}
                  >
                    {LANGUAGE_NAMES[lCode as Lang] || lCode.toUpperCase()}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Card 3: Business Information & WhatsApp Setup */}
          <div className="theme-bg-card border theme-border rounded-3xl p-6 shadow-xl space-y-4">
            <h3 className="text-base font-bold theme-text-main mb-1 flex items-center gap-2">
              <User size={18} className="text-yellow-500" /> {t('settings.profile_header', lang)}
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-mono font-bold theme-text-muted uppercase mb-1">
                  {t('settings.biz_name', lang)}
                </label>
                <input
                  type="text"
                  value={form.business_name || ''}
                  onChange={(e) => update('business_name', e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl theme-bg-input border theme-border theme-text-main text-xs outline-none focus:border-yellow-500/50"
                  placeholder="Shree Ganesh Traders"
                />
              </div>

              <div>
                <label className="block text-xs font-mono font-bold theme-text-muted uppercase mb-1">
                  {t('settings.whatsapp_label', lang)}
                </label>
                <input
                  type="text"
                  value={form.whatsapp_number || ''}
                  onChange={(e) => update('whatsapp_number', e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl theme-bg-input border theme-border theme-text-main text-xs outline-none focus:border-yellow-500/50 font-mono"
                  placeholder="+91 98765 43210"
                />
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
