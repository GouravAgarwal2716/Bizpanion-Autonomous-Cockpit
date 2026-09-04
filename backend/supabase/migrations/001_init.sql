-- ============================================================
-- Bizpanion Database Schema
-- Run this in Supabase SQL Editor (Dashboard → SQL Editor → New query)
-- ============================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ─── Business Profile ──────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS business_profile (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         TEXT UNIQUE NOT NULL,
    business_name   TEXT NOT NULL,
    business_type   TEXT NOT NULL,
    region          TEXT NOT NULL,
    language        TEXT NOT NULL DEFAULT 'en',
    whatsapp_number TEXT,
    alert_sensitivity TEXT NOT NULL DEFAULT 'high',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ─── Transactions ──────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS transactions (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    business_id             UUID NOT NULL REFERENCES business_profile(id) ON DELETE CASCADE,
    date                    TIMESTAMPTZ NOT NULL,
    item_name               TEXT NOT NULL,
    category                TEXT NOT NULL DEFAULT 'other',
    quantity                NUMERIC(12, 3) NOT NULL DEFAULT 0,
    unit                    TEXT NOT NULL DEFAULT 'kg',
    selling_price_per_unit  NUMERIC(10, 2) NOT NULL DEFAULT 0,
    total_amount            NUMERIC(12, 2) NOT NULL DEFAULT 0,
    transaction_type        TEXT NOT NULL DEFAULT 'sale',
    source                  TEXT NOT NULL DEFAULT 'csv',
    raw_row_index           INTEGER,
    flagged                 BOOLEAN DEFAULT FALSE,
    flag_reason             TEXT,
    created_at              TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_transactions_business_date ON transactions(business_id, date DESC);
CREATE INDEX IF NOT EXISTS idx_transactions_item ON transactions(business_id, item_name);

-- ─── Inventory ─────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS inventory (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    business_id     UUID NOT NULL REFERENCES business_profile(id) ON DELETE CASCADE,
    item_name       TEXT NOT NULL,
    category        TEXT NOT NULL DEFAULT 'other',
    current_stock   NUMERIC(12, 3) NOT NULL DEFAULT 0,
    unit            TEXT NOT NULL DEFAULT 'kg',
    reorder_level   NUMERIC(12, 3) DEFAULT 0,
    last_updated    TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(business_id, item_name)
);

-- ─── Market Prices (Agmarknet) ─────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS market_prices (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    commodity       TEXT NOT NULL,
    variety         TEXT,
    market_name     TEXT,
    state           TEXT,
    district        TEXT,
    min_price       NUMERIC(10, 2),
    max_price       NUMERIC(10, 2),
    modal_price     NUMERIC(10, 2) NOT NULL,
    date            TIMESTAMPTZ NOT NULL,
    source          TEXT DEFAULT 'agmarknet',
    UNIQUE(commodity, market_name, date)
);

CREATE INDEX IF NOT EXISTS idx_market_prices_commodity ON market_prices(commodity, date DESC);
CREATE INDEX IF NOT EXISTS idx_market_prices_state ON market_prices(state, commodity);

-- ─── Memory ────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS memory (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    business_id     UUID NOT NULL REFERENCES business_profile(id) ON DELETE CASCADE,
    key             TEXT NOT NULL,
    value           JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(business_id, key)
);

-- ─── Workflow Rules ────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS workflow_rules (
    id                          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    business_id                 UUID NOT NULL UNIQUE REFERENCES business_profile(id) ON DELETE CASCADE,
    underpricing_threshold_pct  NUMERIC(5, 2) DEFAULT 15.0,
    stock_depletion_days        INTEGER DEFAULT 7,
    scheme_deadline_days        INTEGER DEFAULT 7,
    sales_zscore_threshold      NUMERIC(4, 2) DEFAULT 2.0,
    created_at                  TIMESTAMPTZ DEFAULT NOW()
);

-- ─── Alerts Log ────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS alerts_log (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    business_id             UUID NOT NULL REFERENCES business_profile(id) ON DELETE CASCADE,
    alert_type              TEXT NOT NULL,
    severity                TEXT NOT NULL,
    title                   TEXT NOT NULL,
    message                 TEXT NOT NULL,
    message_en              TEXT NOT NULL,
    data_snapshot           JSONB DEFAULT '{}',
    recommended_action      TEXT,
    recommended_action_en   TEXT,
    whatsapp_sent           BOOLEAN DEFAULT FALSE,
    audio_url               TEXT,
    acknowledged            BOOLEAN DEFAULT FALSE,
    created_at              TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_alerts_business ON alerts_log(business_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts_log(business_id, severity, acknowledged);

-- ─── RLS Policies ─────────────────────────────────────────────────────────
-- Backend uses service role key, so RLS is only for frontend direct queries.

ALTER TABLE business_profile ENABLE ROW LEVEL SECURITY;
ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE inventory ENABLE ROW LEVEL SECURITY;
ALTER TABLE alerts_log ENABLE ROW LEVEL SECURITY;

-- Allow users to read their own data
CREATE POLICY "own_profile" ON business_profile FOR ALL USING (user_id = auth.uid()::TEXT);
CREATE POLICY "own_transactions" ON transactions FOR ALL USING (
    business_id IN (SELECT id FROM business_profile WHERE user_id = auth.uid()::TEXT)
);
CREATE POLICY "own_inventory" ON inventory FOR ALL USING (
    business_id IN (SELECT id FROM business_profile WHERE user_id = auth.uid()::TEXT)
);
CREATE POLICY "own_alerts" ON alerts_log FOR ALL USING (
    business_id IN (SELECT id FROM business_profile WHERE user_id = auth.uid()::TEXT)
);

-- Market prices are public (read-only)
ALTER TABLE market_prices ENABLE ROW LEVEL SECURITY;
CREATE POLICY "market_prices_read" ON market_prices FOR SELECT USING (TRUE);

-- ─── Voice Sessions & Advisory Memory ───────────────────────────────────────

CREATE TABLE IF NOT EXISTS voice_sessions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    business_id     UUID NOT NULL REFERENCES business_profile(id) ON DELETE CASCADE,
    session_title   TEXT DEFAULT 'Voice Advisory Session',
    language        TEXT NOT NULL DEFAULT 'en',
    messages        JSONB NOT NULL DEFAULT '[]',
    summary         TEXT,
    action_items    JSONB DEFAULT '[]',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_voice_sessions_business ON voice_sessions(business_id, created_at DESC);

-- ─── Decision Sandbox & Strategy Scenarios ───────────────────────────────────

CREATE TABLE IF NOT EXISTS decision_scenarios (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    business_id         UUID NOT NULL REFERENCES business_profile(id) ON DELETE CASCADE,
    scenario_title      TEXT NOT NULL,
    category            TEXT NOT NULL, -- 'pricing', 'inventory', 'expansion', 'credit'
    problem_statement   TEXT NOT NULL,
    steps               JSONB NOT NULL DEFAULT '[]',
    user_choices        JSONB NOT NULL DEFAULT '{}',
    simulated_impact    JSONB NOT NULL DEFAULT '{}',
    recommended_blueprint TEXT,
    scheme_citations    JSONB DEFAULT '[]',
    status              TEXT DEFAULT 'completed',
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_decision_scenarios_business ON decision_scenarios(business_id, created_at DESC);

-- ─── Updated_at trigger ───────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_business_profile_updated
    BEFORE UPDATE ON business_profile
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_memory_updated
    BEFORE UPDATE ON memory
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_voice_sessions_updated
    BEFORE UPDATE ON voice_sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

