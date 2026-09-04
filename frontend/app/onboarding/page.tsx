'use client';
import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { signup } from '@/lib/api';
import { t, setLang, type Lang } from '@/lib/i18n';
import { ArrowRight, ArrowLeft, Check, Sparkles, Zap } from 'lucide-react';

const BUSINESS_TYPES = [
  { value: 'kirana_shop', label: { en: 'Kirana Shop', hi: 'किराना दुकान', ta: 'கிரானா கடை', te: 'కిరాణా దుకాణం', kn: 'ಕಿರಾಣ ಅಂಗಡಿ' }},
  { value: 'grocery_store', label: { en: 'Grocery Store', hi: 'ग्रोसरी स्टोर', ta: 'மளிகை கடை', te: 'కిరాణా స్టోర్', kn: 'ದಿನಸಿ ಅಂಗಡಿ' }},
  { value: 'dairy_farmer', label: { en: 'Dairy Farmer', hi: 'डेयरी किसान', ta: 'பால் உற்பத்தியாளர்', te: 'డైరీ రైతు', kn: 'ಡೈರಿ ರೈತ' }},
  { value: 'vegetable_vendor', label: { en: 'Vegetable Vendor', hi: 'सब्जी विक्रेता', ta: 'காய்கறி வியாபாரி', te: 'கூరగాయల అమ్మకందారు', kn: 'ತರಕಾರಿ ವ್ಯಾಪಾರಿ' }},
  { value: 'textile', label: { en: 'Textile / Clothing', hi: 'कपड़ा व्यापार', ta: 'ஜவுளி', te: 'వస్త్రాలు', kn: 'ಜವಳಿ' }},
  { value: 'food_processing', label: { en: 'Food Processing', hi: 'खाद्य प्रसंस्करण', ta: 'உணவு பதப்படுத்தல்', te: 'ఆహార ప్రాసెసింగ్', kn: 'ಆಹಾರ ಸಂಸ್ಕರಣೆ' }},
  { value: 'other', label: { en: 'Other', hi: 'अन्य', ta: 'மற்றவை', te: 'ఇතරాలు', kn: 'ಇತರ' }},
];

const LANGUAGES = [
  { value: 'en', label: 'English' },
  { value: 'hi', label: 'हिंदी (Hindi)' },
  { value: 'ta', label: 'தமிழ் (Tamil)' },
  { value: 'te', label: 'తెలుగు (Telugu)' },
  { value: 'kn', label: 'ಕನ್ನಡ (Kannada)' },
];

export default function OnboardingPage() {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [lang, setLangState] = useState<Lang>('en');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const [form, setForm] = useState({
    email: '',
    password: '',
    business_name: '',
    business_type: 'kirana_shop',
    region: 'Maharashtra',
    language: 'en',
    whatsapp_number: '9518948695',
  });

  const update = (k: string, v: string) => setForm(f => ({ ...f, [k]: v }));

  const handleLangChange = (v: string) => {
    update('language', v);
    setLangState(v as Lang);
    setLang(v as Lang);
  };

  async function handleFinish() {
    setLoading(true);
    setError('');
    try {
      if (form.business_name) localStorage.setItem('bizpanion_business_name', form.business_name);
      if (form.business_type) localStorage.setItem('bizpanion_business_type', form.business_type);
      if (form.whatsapp_number) localStorage.setItem('bizpanion_whatsapp', form.whatsapp_number);
      localStorage.setItem('bizpanion_lang', form.language);
      localStorage.setItem('bizpanion_profile', JSON.stringify(form));
      
      await signup(form).catch(() => null);
      router.push('/home');
    } catch (e: any) {
      router.push('/home');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen theme-bg-main theme-text-main flex items-center justify-center p-6 selection:bg-yellow-500 selection:text-slate-950">
      <div className="w-full max-w-lg space-y-6 animate-fade-in">
        {/* Brand Header */}
        <div className="text-center space-y-2">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-gradient-to-tr from-yellow-500 to-amber-400 text-slate-950 font-black text-3xl shadow-xl shadow-yellow-500/20 mb-2">
            B
          </div>
          <h1 className="text-3xl font-extrabold tracking-tight theme-text-main">
            Bizpanion
          </h1>
          <p className="text-xs theme-text-muted">
            {t('onboard.welcome', lang)}
          </p>
        </div>

        {/* Wizard Card */}
        <div className="theme-bg-card border theme-border rounded-3xl p-8 shadow-2xl space-y-6">
          {/* Step Progress Indicators */}
          <div className="flex items-center justify-between gap-2">
            {[0, 1, 2].map((i) => (
              <div
                key={i}
                className={`h-1.5 flex-1 rounded-full transition-all ${
                  i <= step ? 'bg-yellow-500 shadow-sm' : 'theme-bg-input'
                }`}
              />
            ))}
          </div>

          <div className="border-b theme-border pb-3">
            <span className="text-[10px] font-mono font-bold text-yellow-500 uppercase tracking-wider">
              {step === 0 ? 'Step 1 of 3' : step === 1 ? 'Step 2 of 3' : 'Step 3 of 3'}
            </span>
            <h2 className="text-xl font-bold theme-text-main mt-0.5">
              {[t('onboard.step1', lang), t('onboard.step2', lang), t('onboard.step3', lang)][step]}
            </h2>
          </div>

          {/* STEP 0: Enterprise Info */}
          {step === 0 && (
            <div className="space-y-4 animate-fade-in">
              <div>
                <label className="block text-xs font-mono font-bold theme-text-muted uppercase mb-1">
                  {t('onboard.biz_name', lang)}
                </label>
                <input
                  id="biz-name"
                  type="text"
                  value={form.business_name}
                  onChange={e => update('business_name', e.target.value)}
                  placeholder="e.g. Fresh Greens / Ganesh Traders"
                  className="w-full px-4 py-3 rounded-xl theme-bg-input border theme-border theme-text-main text-xs outline-none focus:border-yellow-500/50"
                />
              </div>

              <div>
                <label className="block text-xs font-mono font-bold theme-text-muted uppercase mb-1">
                  {t('onboard.biz_type', lang)}
                </label>
                <select
                  id="biz-type"
                  value={form.business_type}
                  onChange={e => update('business_type', e.target.value)}
                  className="w-full px-4 py-3 rounded-xl theme-bg-input border theme-border theme-text-main text-xs outline-none focus:border-yellow-500/50"
                >
                  {BUSINESS_TYPES.map(bt => (
                    <option key={bt.value} value={bt.value} className="bg-slate-900 text-white">
                      {bt.label[lang as keyof typeof bt.label] || bt.label.en}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-mono font-bold theme-text-muted uppercase mb-1">
                  Email Address
                </label>
                <input
                  id="email"
                  type="email"
                  value={form.email}
                  onChange={e => update('email', e.target.value)}
                  placeholder="owner@enterprise.com"
                  className="w-full px-4 py-3 rounded-xl theme-bg-input border theme-border theme-text-main text-xs outline-none focus:border-yellow-500/50"
                />
              </div>

              <div>
                <label className="block text-xs font-mono font-bold theme-text-muted uppercase mb-1">
                  Password
                </label>
                <input
                  id="password"
                  type="password"
                  value={form.password}
                  onChange={e => update('password', e.target.value)}
                  placeholder="••••••••"
                  className="w-full px-4 py-3 rounded-xl theme-bg-input border theme-border theme-text-main text-xs outline-none focus:border-yellow-500/50"
                />
              </div>
            </div>
          )}

          {/* STEP 1: Region & Language */}
          {step === 1 && (
            <div className="space-y-4 animate-fade-in">
              <div>
                <label className="block text-xs font-mono font-bold theme-text-muted uppercase mb-1">
                  {t('onboard.region', lang)}
                </label>
                <input
                  id="region"
                  type="text"
                  value={form.region}
                  onChange={e => update('region', e.target.value)}
                  placeholder="e.g. Nashik, Maharashtra"
                  className="w-full px-4 py-3 rounded-xl theme-bg-input border theme-border theme-text-main text-xs outline-none focus:border-yellow-500/50"
                />
              </div>

              <div>
                <label className="block text-xs font-mono font-bold theme-text-muted uppercase mb-1">
                  {t('onboard.language', lang)}
                </label>
                <select
                  id="language"
                  value={form.language}
                  onChange={e => handleLangChange(e.target.value)}
                  className="w-full px-4 py-3 rounded-xl theme-bg-input border theme-border theme-text-main text-xs outline-none focus:border-yellow-500/50"
                >
                  {LANGUAGES.map(l => (
                    <option key={l.value} value={l.value} className="bg-slate-900 text-white">
                      {l.label}
                    </option>
                  ))}
                </select>
                <p className="text-[11px] theme-text-muted mt-1.5">
                  All AI alerts, voice briefings, and WhatsApp notifications adapt to this language.
                </p>
              </div>
            </div>
          )}

          {/* STEP 2: WhatsApp Setup */}
          {step === 2 && (
            <div className="space-y-4 animate-fade-in">
              <div>
                <label className="block text-xs font-mono font-bold theme-text-muted uppercase mb-1">
                  {t('onboard.whatsapp', lang)}
                </label>
                <input
                  id="whatsapp"
                  type="text"
                  value={form.whatsapp_number}
                  onChange={e => update('whatsapp_number', e.target.value)}
                  placeholder="+91 95189 48695"
                  className="w-full px-4 py-3 rounded-xl theme-bg-input border theme-border theme-text-main text-xs outline-none focus:border-yellow-500/50 font-mono"
                />
                <p className="text-[11px] theme-text-muted mt-1.5">
                  Autonomous AI notices and executive reports will be dispatched to this WhatsApp number.
                </p>
              </div>

              <div className="p-4 rounded-2xl bg-yellow-500/10 border border-yellow-500/20 text-xs theme-text-main space-y-2">
                <div className="font-bold text-yellow-500 flex items-center gap-1.5">
                  <Zap size={15} /> Autonomous Agent Workflow:
                </div>
                <p className="theme-text-muted leading-relaxed text-[11px]">
                  When you upload ledgers, AI agents analyze Mandi benchmark prices, compute stock depletion velocity, and dispatch actionable recovery notices automatically.
                </p>
              </div>

              {error && (
                <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs">
                  {error}
                </div>
              )}
            </div>
          )}

          {/* Navigation Buttons */}
          <div className="flex items-center gap-3 pt-2">
            {step > 0 && (
              <button
                id="btn-back"
                type="button"
                onClick={() => setStep(s => s - 1)}
                className="flex-1 flex items-center justify-center gap-2 theme-bg-input border theme-border theme-text-main font-bold text-xs py-3 px-4 rounded-xl hover:bg-yellow-500/10 transition-all"
              >
                <ArrowLeft size={15} />
                <span>{t('onboard.back', lang)}</span>
              </button>
            )}

            {step < 2 ? (
              <button
                id="btn-next"
                type="button"
                onClick={() => setStep(s => s + 1)}
                disabled={
                  (step === 0 && (!form.business_name || !form.email || !form.password)) ||
                  (step === 1 && !form.region)
                }
                className="flex-1 flex items-center justify-center gap-2 bg-yellow-500 hover:bg-yellow-400 text-slate-950 font-extrabold text-xs py-3 px-4 rounded-xl shadow-lg shadow-yellow-500/20 transition-all disabled:opacity-50"
              >
                <span>{t('onboard.next', lang)}</span>
                <ArrowRight size={15} />
              </button>
            ) : (
              <button
                id="btn-finish"
                type="button"
                onClick={handleFinish}
                disabled={loading || !form.whatsapp_number}
                className="flex-1 flex items-center justify-center gap-2 bg-yellow-500 hover:bg-yellow-400 text-slate-950 font-extrabold text-xs py-3 px-4 rounded-xl shadow-lg shadow-yellow-500/20 transition-all disabled:opacity-50"
              >
                {loading ? 'Creating account...' : t('onboard.finish', lang)}
                <Sparkles size={15} />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
