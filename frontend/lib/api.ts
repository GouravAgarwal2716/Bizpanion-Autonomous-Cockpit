/**
 * API client — calls the FastAPI backend.
 * All functions are async and throw on HTTP errors.
 */

export const getApiUrl = () => {
  if (typeof window !== 'undefined' && window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
    return 'https://bizpanion-autonomous-cockpit-backend.onrender.com';
  }
  return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
};

const API_URL = getApiUrl();

async function apiFetch(path: string, options?: RequestInit) {
  const token = typeof window !== 'undefined' ? localStorage.getItem('bizpanion_token') : null;
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options?.headers,
    },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Unknown error' }));
    const detailMsg = typeof err.detail === 'string' ? err.detail : (typeof err.detail === 'object' ? JSON.stringify(err.detail) : `HTTP ${res.status}`);
    throw new Error(detailMsg || `HTTP ${res.status}`);
  }
  return res;
}

// ── Auth ─────────────────────────────────────────────────────────────────────

export async function login(email: string, password: string) {
  const res = await apiFetch(`/api/auth/login?email=${encodeURIComponent(email)}&password=${encodeURIComponent(password)}`, { method: 'POST' });
  const data = await res.json();
  if (typeof window !== 'undefined') {
    localStorage.setItem('bizpanion_token', data.access_token);
    localStorage.setItem('bizpanion_user_id', data.user_id);
    localStorage.setItem('bizpanion_business_id', data.profile?.id || '');
  }
  return data;
}

export async function signup(payload: {
  email: string; password: string; business_name: string;
  business_type: string; region: string; language: string; whatsapp_number: string;
}) {
  const res = await apiFetch('/api/auth/signup', { method: 'POST', body: JSON.stringify(payload) });
  const data = await res.json();
  if (typeof window !== 'undefined') {
    localStorage.setItem('bizpanion_user_id', data.user_id);
    localStorage.setItem('bizpanion_business_id', data.business_id);
  }
  return data;
}

export function getStoredBusinessId(): string {
  if (typeof window === 'undefined') return 'biz-demo-123';
  return localStorage.getItem('bizpanion_business_id') || 'biz-demo-123';
}

export function getStoredUserId(): string {
  if (typeof window === 'undefined') return 'demo-user-123';
  return localStorage.getItem('bizpanion_user_id') || 'demo-user-123';
}

export async function getProfile(userId: string) {
  let localData: any = {};
  if (typeof window !== 'undefined') {
    const saved = localStorage.getItem('bizpanion_profile');
    if (saved) {
      try { localData = JSON.parse(saved); } catch {}
    }
    if (localStorage.getItem('bizpanion_business_name')) {
      localData.business_name = localStorage.getItem('bizpanion_business_name');
    }
    if (localStorage.getItem('bizpanion_business_type')) {
      localData.business_type = localStorage.getItem('bizpanion_business_type');
    }
    if (localStorage.getItem('bizpanion_whatsapp')) {
      localData.whatsapp_number = localStorage.getItem('bizpanion_whatsapp');
    }
    if (localStorage.getItem('bizpanion_lang')) {
      localData.language = localStorage.getItem('bizpanion_lang');
    }
  }
  try {
    const res = await apiFetch(`/api/auth/profile/${userId || 'demo-user-123'}`);
    const data = await res.json();
    return { ...data, ...localData };
  } catch {
    const defaultName = typeof window !== 'undefined' ? (localStorage.getItem('bizpanion_business_name') || 'Enterprise Store') : 'Enterprise Store';
    const defaultType = typeof window !== 'undefined' ? (localStorage.getItem('bizpanion_business_type') || 'kirana_shop') : 'kirana_shop';
    const defaultPhone = typeof window !== 'undefined' ? (localStorage.getItem('bizpanion_whatsapp') || '9518948695') : '9518948695';
    const defaultLang = typeof window !== 'undefined' ? (localStorage.getItem('bizpanion_lang') || 'en') : 'en';
    return {
      business_name: defaultName,
      business_type: defaultType,
      whatsapp_number: defaultPhone,
      language: defaultLang,
      region: 'Maharashtra',
      ...localData
    };
  }
}

export async function updateProfile(userId: string, data: Record<string, unknown>) {
  if (typeof window !== 'undefined') {
    const existing = localStorage.getItem('bizpanion_profile');
    const prev = existing ? JSON.parse(existing) : {};
    const updated = { ...prev, ...data };
    localStorage.setItem('bizpanion_profile', JSON.stringify(updated));

    if (data.whatsapp_number) {
      localStorage.setItem('bizpanion_whatsapp', String(data.whatsapp_number));
    }
    if (data.business_name) {
      localStorage.setItem('bizpanion_business_name', String(data.business_name));
    }
    if (data.business_type) {
      localStorage.setItem('bizpanion_business_type', String(data.business_type));
    }
    if (data.language) {
      localStorage.setItem('bizpanion_lang', String(data.language));
    }
  }
  try {
    const res = await apiFetch(`/api/auth/profile/${userId || 'demo-user-123'}`, { method: 'PATCH', body: JSON.stringify(data) });
    const backendData = await res.json().catch(() => ({}));
    const localData = typeof window !== 'undefined' && localStorage.getItem('bizpanion_profile') 
      ? JSON.parse(localStorage.getItem('bizpanion_profile')!) 
      : data;
    return { ...backendData, ...localData };
  } catch {
    return typeof window !== 'undefined' && localStorage.getItem('bizpanion_profile') 
      ? JSON.parse(localStorage.getItem('bizpanion_profile')!) 
      : data;
  }
}

// ── Alerts ───────────────────────────────────────────────────────────────────

export async function getAlerts(businessId: string, limit = 50) {
  const res = await apiFetch(`/api/alerts/${businessId}?limit=${limit}`);
  return res.json();
}

export async function getAlertsSummary(businessId: string) {
  const res = await apiFetch(`/api/alerts/${businessId}/summary`);
  return res.json();
}

export async function acknowledgeAlert(alertId: string) {
  const res = await apiFetch(`/api/alerts/${alertId}/acknowledge`, { method: 'PATCH' });
  return res.json();
}

// ── Voice / TTS ───────────────────────────────────────────────────────────────

export async function getDailyBriefing(businessId: string, language: string, businessName?: string, businessType?: string) {
  const bizName = businessName || (typeof window !== 'undefined' ? localStorage.getItem('bizpanion_business_name') : null);
  const bizType = businessType || (typeof window !== 'undefined' ? localStorage.getItem('bizpanion_business_type') : null);
  const res = await apiFetch('/api/voice/briefing', {
    method: 'POST',
    body: JSON.stringify({ business_id: businessId, language, business_name: bizName, business_type: bizType }),
  });
  return res.json();
}

export async function getAlertAudio(alertId: string) {
  const res = await apiFetch(`/api/voice/alert/${alertId}/audio`);
  return res.json();
}

// ── Agents ───────────────────────────────────────────────────────────────────

export async function runAgents(businessId: string, trigger = 'manual') {
  const res = await apiFetch('/api/agents/run', {
    method: 'POST',
    body: JSON.stringify({ business_id: businessId, trigger }),
  });
  return res.json();
}

// ── Tally ─────────────────────────────────────────────────────────────────────

export async function checkTallyConnection(businessId: string, tallyUrl = 'http://localhost:9000') {
  const res = await apiFetch('/api/tally/check', {
    method: 'POST',
    body: JSON.stringify({ business_id: businessId, tally_url: tallyUrl }),
  });
  return res.json();
}

export async function syncFromTally(businessId: string, daysBack = 30) {
  const res = await apiFetch('/api/tally/sync', {
    method: 'POST',
    body: JSON.stringify({ business_id: businessId, days_back: daysBack }),
  });
  return res.json();
}

// ── Market ────────────────────────────────────────────────────────────────────

export async function getMarketPrice(commodity: string, state = '') {
  const res = await apiFetch(`/api/market/price?commodity=${encodeURIComponent(commodity)}&state=${encodeURIComponent(state)}`);
  return res.json();
}

// ── CSV Upload (SSE streaming) ────────────────────────────────────────────────

export function uploadCSV(
  file: File,
  businessId: string,
  onStep: (step: UploadStep) => void,
  language?: string,
): Promise<UploadComplete> {
  return new Promise((resolve, reject) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('business_id', businessId);
    if (language) {
      formData.append('language', language);
    }

    const token = typeof window !== 'undefined' ? localStorage.getItem('bizpanion_token') : null;

    fetch(`${API_URL}/api/upload/csv`, {
      method: 'POST',
      body: formData,
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    }).then(res => {
      const reader = res.body?.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      function pump(): Promise<void> {
        return reader!.read().then(({ done, value }) => {
          if (done) return;
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6));
                if (data.type === 'complete') resolve(data as UploadComplete);
                else onStep(data as UploadStep);
              } catch {}
            }
          }
          return pump();
        });
      }

      pump().catch(reject);
    }).catch(reject);
  });
}

export interface UploadStep {
  type: 'step';
  step: string;
  status: 'running' | 'done' | 'error';
  message: string;
  detail?: string;
}

export interface UploadComplete {
  type: 'complete';
  upload_id: string;
  rows_total: number;
  rows_cleaned: number;
  rows_flagged: number;
  cleaned_csv_url: string;
}

// ── Voice Session (Gemini Live Style) ────────────────────────────────────────

export async function startVoiceSession(businessId: string, language = 'en') {
  const bizName = typeof window !== 'undefined' ? localStorage.getItem('bizpanion_business_name') : null;
  const bizType = typeof window !== 'undefined' ? localStorage.getItem('bizpanion_business_type') : null;
  const res = await apiFetch('/api/voice/session/start', {
    method: 'POST',
    body: JSON.stringify({ business_id: businessId, language, business_name: bizName, business_type: bizType }),
  });
  return res.json();
}

export async function sendVoiceTurn(payload: {
  session_id: string;
  business_id: string;
  user_speech: string;
  language?: string;
  business_name?: string;
  business_type?: string;
}) {
  const bizName = typeof window !== 'undefined' ? localStorage.getItem('bizpanion_business_name') : null;
  const bizType = typeof window !== 'undefined' ? localStorage.getItem('bizpanion_business_type') : null;
  const res = await apiFetch('/api/voice/session/turn', {
    method: 'POST',
    body: JSON.stringify({ business_name: bizName, business_type: bizType, ...payload }),
  });
  return res.json();
}

export async function getVoiceSessions(businessId: string) {
  const res = await apiFetch(`/api/voice/sessions/${businessId}`);
  return res.json();
}

// ── Decision Sandbox & Strategy Simulator ────────────────────────────────────

export async function getDecisionScenarios(businessId: string) {
  const res = await apiFetch(`/api/decisions/scenarios/${businessId}`);
  return res.json();
}

export async function simulateDecision(payload: {
  business_id: string;
  scenario: any;
  choices: Record<number, string>;
  language?: string;
}) {
  const res = await apiFetch('/api/decisions/simulate', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
  return res.json();
}

export async function saveDecision(payload: any) {
  const res = await apiFetch('/api/decisions/save', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
  return res.json();
}

export async function getDecisionHistory(businessId: string) {
  const res = await apiFetch(`/api/decisions/history/${businessId}`);
  return res.json();
}

export async function getDashboardOverview(businessId: string) {
  const res = await apiFetch(`/api/dashboard/overview/${businessId}`);
  return res.json();
}

// ── Demo & Simulation Helpers ────────────────────────────────────────────────

export async function loadSampleDataset(businessId: string, sector: string, language?: string) {
  const res = await apiFetch('/api/upload/load-sample', {
    method: 'POST',
    body: JSON.stringify({ business_id: businessId, sector, language }),
  });
  return res.json();
}

export async function simulateTallySync(businessId: string) {
  const res = await apiFetch('/api/tally/simulate-sync', {
    method: 'POST',
    body: JSON.stringify({ business_id: businessId }),
  });
  return res.json();
}



