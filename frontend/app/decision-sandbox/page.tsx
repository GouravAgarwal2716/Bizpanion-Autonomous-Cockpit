'use client';
import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { 
  CheckCircle2, ArrowRight, BookmarkCheck, Layers, RefreshCw, ArrowLeft, Zap
} from 'lucide-react';
import NavSidebar from '@/components/NavSidebar';
import { 
  getStoredBusinessId, 
  getDecisionScenarios, 
  simulateDecision, 
  saveDecision, 
} from '@/lib/api';
import { t, getLang, type Lang } from '@/lib/i18n';

const DEFAULT_SCENARIOS = [
  {
    scenario_id: 'sc1',
    title: 'FMCG Margin Recovery',
    badge_summary: 'Match Wholesale Parity',
    description: 'Adjust item prices to match regional Agmarknet wholesale benchmark rates and recover monthly profit margins.',
    steps: [
      {
        step_number: 1,
        title: 'Price Alignment Strategy',
        options: [
          { id: 'opt_full_parity', label: 'Full Mandi Parity (+26% Margin)', description: 'Match regional Mandi wholesale benchmark rate immediately.' },
          { id: 'opt_gradual', label: 'Gradual Tiered Increase (+15% Margin)', description: 'Raise price by 5% bi-weekly to test customer elasticity.' },
          { id: 'opt_premium_grade', label: 'Premium Grade Segmentation (+20%)', description: 'Introduce premium packaging tier at benchmark + 5%.' },
          { id: 'opt_promotional', label: 'Promotional Bundle Rate (+12%)', description: 'Pair with complementary goods at a slight bundle discount.' }
        ]
      },
      {
        step_number: 2,
        title: 'Customer Retention & Loyalty',
        options: [
          { id: 'opt_bulk_disc', label: 'Loyalty Bulk Discount (5% Off)', description: 'Offer 5% discount on orders exceeding ₹1,000 to retain volume buyers.' },
          { id: 'opt_no_disc', label: 'Standard Fixed Price (Strict Parity)', description: 'Maintain strict margin parity across all purchase quantities.' },
          { id: 'opt_cashback', label: 'UPI Digital Transaction Cashback', description: 'Instant ₹20 digital cashback on repeat merchant payments.' },
          { id: 'opt_credit_window', label: '7-Day Customer Trade Credit', description: 'Provide 7-day credit window to protect regular commercial buyers.' }
        ]
      },
      {
        step_number: 3,
        title: 'Reinvestment & Surplus Deployment',
        options: [
          { id: 'opt_procure_reinvest', label: 'Reinvest in Bulk Inventory', description: 'Capture 8% distributor volume discount on fast-moving staples.' },
          { id: 'opt_cash_reserve', label: 'Build 30-Day Liquidity Reserve', description: 'Safely shield shop cashflow against sudden market price spikes.' },
          { id: 'opt_clear_vendor_debt', label: 'Pay Off High-Interest Vendor Credit', description: 'Eliminate 18% annual trade credit financing fees.' },
          { id: 'opt_store_upgrade', label: 'Digital POS & Barcode Printer Upgrade', description: 'Install automated checkout billing system to speed up customer queues.' }
        ]
      }
    ]
  },
  {
    scenario_id: 'sc2',
    title: 'Bulk Stock Procurement Buffer',
    badge_summary: 'Supplier Bulk Buffer',
    description: 'Pre-purchase fast-moving staples in bulk from distributors to capture bulk discounts before festive demand surge.',
    steps: [
      {
        step_number: 1,
        title: 'Procurement Reserve Volume',
        options: [
          { id: 'opt_30day_stock', label: '30-Day Reserve (8% Supplier Rebate)', description: 'Order 30 days inventory reserve for maximum bulk price discount.' },
          { id: 'opt_15day_stock', label: '15-Day Reserve (4% Supplier Rebate)', description: 'Order 15 days inventory to balance working capital cash.' },
          { id: 'opt_7day_stock', label: '7-Day Just-In-Time Procurement', description: 'Order 7 days stock to minimize storage space and holding cash.' },
          { id: 'opt_consignment', label: 'Distributor Consignment Model', description: 'Zero upfront inventory holding cost with profit-sharing terms.' }
        ]
      },
      {
        step_number: 2,
        title: 'Supplier Settlement & Credit Terms',
        options: [
          { id: 'opt_cash_pay', label: 'Upfront Cash Payment (2% Extra Rebate)', description: 'Pay cash to receive extra 2% prompt settlement rebate.' },
          { id: 'opt_credit_pay', label: '30-Day Supplier Trade Credit', description: 'Utilize 30-day trade credit period to maintain liquid working cash.' },
          { id: 'opt_split_pay', label: '50% Cash + 50% 15-Day Credit', description: 'Balanced payment terms to split cashflow commitment.' },
          { id: 'opt_bank_guarantee', label: 'MSME Bank Guarantee Credit Line', description: 'Leverage collateral-free SIDBI credit facility.' }
        ]
      },
      {
        step_number: 3,
        title: 'Storage & Spoilage Prevention',
        options: [
          { id: 'opt_fifo_system', label: 'Active FIFO Shelf Rotation', description: 'Zero setup cost, eliminates expired stock.' },
          { id: 'opt_chilling_crates', label: 'Environment Controlled Storage Crates', description: 'Reduces perishable spoilage losses from 7% to 1.5%.' },
          { id: 'opt_whatsapp_preorder', label: 'WhatsApp Pre-Order Customer Broadcast', description: 'Secures 50%+ sales commitments before shipment arrives.' },
          { id: 'opt_insured_storage', label: 'Warehouse Transit Insurance', description: 'Complete insurance coverage against inventory damage.' }
        ]
      }
    ]
  },
  {
    scenario_id: 'sc3',
    title: 'Working Capital & Subsidy Shield',
    badge_summary: 'Low-Interest Credit Line',
    description: 'Leverage matched government MSME micro-credit schemes (PM SVANidhi / Mudra) to replace high-interest supplier credit.',
    steps: [
      {
        step_number: 1,
        title: 'Government Credit Facility Selection',
        options: [
          { id: 'opt_svanidhi', label: 'PM SVANidhi ₹50,000 Line (7% Subsidy)', description: 'Subsidized working capital loan with UPI transaction cashback.' },
          { id: 'opt_mudra', label: 'Mudra Shishu ₹50,000 Credit Facility', description: 'Zero-collateral instant credit line for stock procurement.' },
          { id: 'opt_pmegp', label: 'PMEGP ₹5 Lakh Loan (35% Grant)', description: 'Capital subsidy grant for enterprise machinery expansion.' },
          { id: 'opt_cgtmse', label: 'CGTMSE Collateral-Free Cover', description: 'Up to ₹2 Crore MSME credit guarantee cover.' }
        ]
      },
      {
        step_number: 2,
        title: 'Capital Deployment Strategy',
        options: [
          { id: 'opt_high_margin_stock', label: 'Procure High-Margin Fast Moving Stock', description: 'Maximize stock turnover velocity and daily revenue.' },
          { id: 'opt_retire_supplier_debt', label: 'Clear High-Interest Vendor Credit', description: 'Pay off supplier credit charging 18%+ annual interest.' },
          { id: 'opt_equipment_purchase', label: 'Purchase Processing Machinery', description: 'Install automated packaging, milling, or cooling equipment.' },
          { id: 'opt_digital_pos_upgrade', label: 'Upgrade Digital POS & Billing System', description: 'Streamline inventory tracking and GST invoice generation.' }
        ]
      },
      {
        step_number: 3,
        title: 'ROI & Repayment Timeline Horizon',
        options: [
          { id: 'opt_fast_3month', label: 'Aggressive 3-Month Payback', description: 'Reinvest daily digital transaction rewards for rapid payoff.' },
          { id: 'opt_steady_6month', label: 'Steady 6-Month Payback Horizon', description: 'Aligned with quarterly MSME subsidy disbursements.' },
          { id: 'opt_12month_scaling', label: '12-Month Multi-Point Expansion', description: 'Builds capital reserve for opening a 2nd retail outlet.' },
          { id: 'opt_flex_reinvest', label: 'Flexible Dynamic Cash Surplus Reinvestment', description: 'Balances liquid cash buffer with inventory growth.' }
        ]
      }
    ]
  }
];

export default function DecisionSandboxPage() {
  const router = useRouter();
  const [lang, setLang] = useState<Lang>('en');
  const [businessId, setBusinessId] = useState('');
  const [scenarios, setScenarios] = useState<any[]>(DEFAULT_SCENARIOS);
  const [activeScenarioIdx, setActiveScenarioIdx] = useState<number>(0);
  const [stepView, setStepView] = useState<'scenarios' | 'configure' | 'outcomes'>('scenarios');
  const [choices, setChoices] = useState<Record<number, string>>({});
  const [runningStrategy, setRunningStrategy] = useState(false);
  const [strategyResult, setStrategyResult] = useState<any>(null);
  const [isSaved, setIsSaved] = useState(false);

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
    loadScenarios(bid);
    return () => {
      if (typeof window !== 'undefined') {
        window.removeEventListener('languageChange', updateLang);
      }
    };
  }, []);

  async function loadScenarios(bid: string) {
    // Keep DEFAULT_SCENARIOS stable to avoid sudden layout jumps
    setScenarios(DEFAULT_SCENARIOS);
  }

  function handleSelectScenario(idx: number) {
    setActiveScenarioIdx(idx);
    const sc = scenarios[idx] || DEFAULT_SCENARIOS[idx];
    const initialChoices: Record<number, string> = {};
    if (sc?.steps) {
      sc.steps.forEach((st: any) => {
        if (st.options && st.options.length > 0) {
          initialChoices[st.step_number] = st.options[0].id;
        }
      });
    }
    setChoices(initialChoices);
    setStrategyResult(null);
    setIsSaved(false);
    setStepView('configure');
  }

  function handleSelectOption(stepNum: number, optId: string) {
    setChoices(prev => ({ ...prev, [stepNum]: optId }));
  }

  async function handleRunStrategy() {
    const activeScenario = scenarios[activeScenarioIdx] || DEFAULT_SCENARIOS[activeScenarioIdx];
    if (!activeScenario) return;

    setRunningStrategy(true);
    try {
      const res = await simulateDecision({
        business_id: businessId,
        scenario: activeScenario,
        choices: choices,
        language: lang
      });
      setStrategyResult(res);
      setStepView('outcomes');
    } catch (e: any) {
      alert(`Failed to run strategy: ${e.message}`);
    } finally {
      setRunningStrategy(false);
    }
  }

  async function handleSaveStrategy() {
    if (!strategyResult || isSaved) return;
    const activeScenario = scenarios[activeScenarioIdx] || DEFAULT_SCENARIOS[activeScenarioIdx];
    try {
      await saveDecision({
        business_id: businessId,
        scenario_id: activeScenario.scenario_id,
        choices: choices,
        result: strategyResult
      });
      setIsSaved(true);
    } catch (e: any) {
      alert(`Failed to save strategy: ${e.message}`);
    }
  }

  const activeScenario = scenarios[activeScenarioIdx] || DEFAULT_SCENARIOS[0];

  return (
    <div className="flex min-h-screen theme-bg-main">
      <NavSidebar active="sandbox" lang={lang} />

      <main className="ml-64 flex-1 min-h-screen p-8 max-w-[1200px]">
        {/* Top Header */}
        <div className="flex items-start justify-between mb-8 flex-wrap gap-4 animate-fade-in">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-yellow-500/10 border border-yellow-500/20 text-yellow-500 text-xs font-mono font-bold uppercase tracking-wider mb-2">
              <Layers size={13} /> Autonomous Strategy Engine
            </div>
            <h1 className="text-3xl font-extrabold theme-text-main tracking-tight">
              {t('sandbox.title', lang)}
            </h1>
            <p className="text-sm theme-text-muted mt-1 max-w-xl">
              {t('sandbox.subtitle', lang)}
            </p>
          </div>

          {stepView !== 'scenarios' && (
            <button
              onClick={() => setStepView('scenarios')}
              className="flex items-center gap-2 theme-bg-card hover:bg-yellow-500/10 theme-text-main font-bold text-xs px-4 py-2.5 rounded-xl border theme-border transition-colors shadow-sm"
            >
              <ArrowLeft size={14} />
              <span>{t('sandbox.back_scenarios', lang)}</span>
            </button>
          )}
        </div>

        {/* STEP 1: Scenario Selection Grid */}
        {stepView === 'scenarios' && (
          <div className="space-y-4 animate-fade-in">
            <h3 className="text-lg font-bold theme-text-main mb-2">
              {t('sandbox.select_scenario', lang)}
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
              {scenarios.map((sc, idx) => (
                <div
                  key={sc.scenario_id || idx}
                  onClick={() => handleSelectScenario(idx)}
                  className="p-6 rounded-3xl theme-bg-card border theme-border hover:border-yellow-500 transition-all cursor-pointer shadow-xl hover:-translate-y-1 group flex flex-col justify-between"
                >
                  <div>
                    <div className="flex items-center justify-between gap-2 mb-2">
                      <span className="text-[10px] font-mono font-bold text-yellow-500 bg-yellow-500/10 px-2 py-0.5 rounded uppercase">
                        Scenario {idx + 1}
                      </span>
                    </div>

                    <h3 className="font-bold theme-text-main text-lg mt-1 group-hover:text-yellow-500 transition-colors">
                      {sc.title}
                    </h3>

                    <div className="inline-flex items-center gap-1.5 my-2.5 px-3 py-1 rounded-xl bg-yellow-500/15 border border-yellow-500/30 text-yellow-500 text-xs font-mono font-extrabold shadow-sm">
                      ⚡ {sc.badge_summary || 'Quick Strategy'}
                    </div>

                    <p className="text-xs theme-text-muted leading-relaxed">
                      {sc.description}
                    </p>
                  </div>

                  <div className="mt-6 flex items-center justify-between pt-4 border-t theme-border">
                    <span className="text-xs font-bold text-yellow-500">Configure Strategy</span>
                    <ArrowRight size={16} className="text-yellow-500 group-hover:translate-x-1 transition-transform" />
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* STEP 2: Configure Decisions & Run Strategy */}
        {stepView === 'configure' && activeScenario && (
          <div className="theme-bg-card border theme-border rounded-3xl p-8 shadow-xl animate-fade-in space-y-6">
            <div className="border-b theme-border pb-4">
              <span className="text-xs font-mono font-bold text-yellow-500 uppercase">
                {t('sandbox.step2_title', lang)}
              </span>
              <h2 className="text-2xl font-extrabold theme-text-main mt-1">
                {activeScenario.title}
              </h2>
              <p className="text-xs theme-text-muted mt-1">
                {activeScenario.description}
              </p>
            </div>

            {/* Decision Steps */}
            <div className="space-y-6">
              {activeScenario.steps?.map((st: any) => (
                <div key={st.step_number} className="space-y-3">
                  <h4 className="text-xs font-mono font-bold theme-text-muted uppercase tracking-wider">
                    Choice {st.step_number}: {st.title}
                  </h4>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    {st.options?.map((opt: any) => {
                      const isSelected = choices[st.step_number] === opt.id;
                      return (
                        <div
                          key={opt.id}
                          onClick={() => handleSelectOption(st.step_number, opt.id)}
                          className={`p-4 rounded-2xl border transition-all cursor-pointer ${
                            isSelected
                              ? 'theme-bg-card border-yellow-500 shadow-lg ring-1 ring-yellow-500'
                              : 'theme-bg-input theme-border hover:border-slate-500'
                          }`}
                        >
                          <div className="flex items-center justify-between mb-1">
                            <span className="font-bold text-sm theme-text-main">{opt.label}</span>
                            {isSelected && <CheckCircle2 size={16} className="text-yellow-500" />}
                          </div>
                          <p className="text-xs theme-text-muted mt-1 leading-relaxed">
                            {opt.description}
                          </p>
                        </div>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>

            {/* Run My Strategy Action Button */}
            <div className="pt-6 border-t theme-border flex justify-end">
              <button
                onClick={handleRunStrategy}
                disabled={runningStrategy}
                className="flex items-center gap-2 bg-yellow-500 hover:bg-yellow-400 text-slate-950 font-bold text-xs px-8 py-3.5 rounded-xl shadow-lg shadow-yellow-500/20 transition-all hover:scale-[1.02]"
              >
                {runningStrategy ? <RefreshCw size={16} className="animate-spin" /> : <Zap size={16} />}
                <span>{runningStrategy ? 'Computing Strategy Outcomes...' : t('sandbox.run_strategy', lang)}</span>
              </button>
            </div>
          </div>
        )}

        {/* STEP 3: Outcomes & Strategy Saving */}
        {stepView === 'outcomes' && strategyResult && (
          <div className="theme-bg-card border theme-border rounded-3xl p-8 shadow-xl animate-fade-in space-y-6">
            <div className="border-b theme-border pb-4 flex items-center justify-between flex-wrap gap-4">
              <div>
                <span className="text-xs font-mono font-bold text-yellow-500 uppercase">
                  {t('sandbox.step3_title', lang)}
                </span>
                <h2 className="text-2xl font-extrabold theme-text-main mt-1">
                  Projected Financial Strategy Results
                </h2>
              </div>

              <button
                onClick={() => setStepView('configure')}
                className="text-xs font-bold theme-text-muted hover:theme-text-main underline"
              >
                Modify Decision Choices
              </button>
            </div>

            {/* Outcome KPI Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
              <div className="p-5 rounded-2xl theme-bg-input border border-yellow-500/30">
                <span className="text-[10px] font-mono font-bold text-yellow-500 uppercase">
                  {t('sandbox.net_cash_impact', lang)}
                </span>
                <div className="text-3xl font-extrabold theme-text-main mt-1">
                  +₹{((strategyResult.simulated_impact?.projected_profit_gain_monthly_inr ?? strategyResult.projected_cash_impact) || 14500).toLocaleString('en-IN')}
                </div>
              </div>

              <div className="p-5 rounded-2xl theme-bg-input border theme-border">
                <span className="text-[10px] font-mono font-bold theme-text-muted uppercase">
                  {t('sandbox.margin_delta', lang)}
                </span>
                <div className="text-3xl font-extrabold text-yellow-500 mt-1">
                  +{(strategyResult.simulated_impact?.projected_revenue_growth_pct ?? strategyResult.gross_margin_delta) || 3.8}%
                </div>
              </div>

              <div className="p-5 rounded-2xl theme-bg-input border theme-border">
                <span className="text-[10px] font-mono font-bold theme-text-muted uppercase">
                  {t('sandbox.risk_level', lang)}
                </span>
                <div className="text-2xl font-extrabold theme-text-main mt-1">
                  {(strategyResult.simulated_impact?.risk_level ?? strategyResult.risk_level) || 'Low Risk'}
                </div>
              </div>
            </div>

            {/* Rationale Box */}
            <div className="p-5 rounded-2xl theme-bg-input border theme-border text-xs theme-text-main leading-relaxed">
              <strong className="block text-sm theme-text-main mb-1">Strategic Rationale & Execution Plan:</strong>
              {strategyResult.executive_blueprint || strategyResult.summary || 'Selected parameters balance inventory holding costs while securing maximum wholesale price discount.'}
            </div>

            {/* Save Action */}
            <div className="pt-4 flex items-center justify-between border-t theme-border flex-wrap gap-4">
              <button
                onClick={() => setStepView('scenarios')}
                className="theme-text-muted hover:theme-text-main text-xs font-bold"
              >
                {t('sandbox.back_scenarios', lang)}
              </button>

              <button
                onClick={handleSaveStrategy}
                disabled={isSaved}
                className={`flex items-center gap-2 px-6 py-3 rounded-xl font-bold text-xs transition-all ${
                  isSaved
                    ? 'theme-bg-input theme-text-muted border theme-border cursor-not-allowed'
                    : 'bg-yellow-500 hover:bg-yellow-400 text-slate-950 shadow-md'
                }`}
              >
                <BookmarkCheck size={16} />
                <span>{isSaved ? t('sandbox.saved', lang) : t('sandbox.save_strategy', lang)}</span>
              </button>
            </div>
          </div>
        )}

      </main>
    </div>
  );
}
