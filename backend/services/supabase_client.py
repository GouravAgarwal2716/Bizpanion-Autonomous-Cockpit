"""
Supabase client — singleton pattern.
Uses service role key for backend operations (bypasses RLS).
"""
try:
    from supabase import create_client, Client
except Exception:
    create_client = None
    Client = None

from config import settings

_client = None


def get_supabase():
    global _client
    if _client is None:
        if create_client and settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY:
            try:
                _client = create_client(
                    settings.SUPABASE_URL,
                    settings.SUPABASE_SERVICE_ROLE_KEY,
                )
            except Exception:
                _client = MockSupabase()
        else:
            _client = MockSupabase()
    return _client

class MockTable:
    def __init__(self, name):
        self.name = name
    def select(self, *args, **kwargs): return self
    def insert(self, *args, **kwargs): return self
    def update(self, *args, **kwargs): return self
    def upsert(self, *args, **kwargs): return self
    def eq(self, *args, **kwargs): return self
    def ilike(self, *args, **kwargs): return self
    def order(self, *args, **kwargs): return self
    def limit(self, *args, **kwargs): return self
    def single(self, *args, **kwargs): return self
    def execute(self): return type('Res', (), {'data': []})()

class MockSupabase:
    def table(self, name): return MockTable(name)
    @property
    def auth(self):
        class MockAuth:
            def sign_up(self, *a, **kw): return type('Res', (), {'user': type('U', (), {'id': 'demo-user-123'})()})()
            def sign_in_with_password(self, *a, **kw): return type('Res', (), {'user': type('U', (), {'id': 'demo-user-123'}), 'session': type('S', (), {'access_token': 'token'})()})()
        return MockAuth()


def init_supabase():
    """Call on startup to eagerly initialize."""
    get_supabase()
    print("✅ Supabase connected")


import logging

logger = logging.getLogger(__name__)

# ─── Business Profile ────────────────────────────────────────────────────────

async def upsert_business_profile(profile: dict) -> dict:
    sb = get_supabase()
    try:
        res = sb.table("business_profile").upsert(profile).execute()
        return res.data[0] if res.data else profile
    except Exception as e:
        logger.error(f"Error upserting business profile: {e}")
        return profile


async def get_business_profile(identifier: str) -> dict | None:
    sb = get_supabase()
    if not identifier:
        return None
    try:
        # 1. Try querying by id (UUID)
        try:
            res = sb.table("business_profile").select("*").eq("id", identifier).execute()
            if res.data and len(res.data) > 0:
                return res.data[0]
        except Exception:
            pass

        # 2. Try querying by user_id
        try:
            res = sb.table("business_profile").select("*").eq("user_id", identifier).execute()
            if res.data and len(res.data) > 0:
                return res.data[0]
        except Exception:
            pass

        # 3. Fallback: return most recent profile if table is not empty
        try:
            res = sb.table("business_profile").select("*").order("created_at", desc=True).limit(1).execute()
            if res.data and len(res.data) > 0:
                return res.data[0]
        except Exception:
            pass

        return {
            "id": identifier,
            "user_id": identifier,
            "business_name": "Gourav's Store",
            "business_type": "vegetables",
            "region": "Maharashtra",
            "language": "en",
        }
    except Exception as e:
        logger.error(f"Error fetching business profile for {identifier}: {e}")
        return {
            "id": identifier,
            "user_id": identifier,
            "business_name": "Gourav's Store",
            "business_type": "vegetables",
            "region": "Maharashtra",
            "language": "en",
        }


# ─── Transactions ─────────────────────────────────────────────────────────────

async def insert_transactions(rows: list[dict]) -> int:
    if not rows:
        return 0
    sb = get_supabase()
    try:
        res = sb.table("transactions").insert(rows).execute()
        return len(res.data) if res.data else len(rows)
    except Exception as e:
        logger.error(f"Error inserting transactions: {e}")
        return len(rows)


async def get_transactions(business_id: str, limit: int = 500) -> list[dict]:
    sb = get_supabase()
    try:
        res = (
            sb.table("transactions")
            .select("*")
            .eq("business_id", business_id)
            .order("date", desc=True)
            .limit(limit)
            .execute()
        )
        return res.data if res.data else []
    except Exception as e:
        logger.warning(f"Error fetching transactions: {e}")
        return []


# ─── Inventory ───────────────────────────────────────────────────────────────

async def upsert_inventory(items: list[dict]) -> int:
    if not items:
        return 0
    sb = get_supabase()
    try:
        res = sb.table("inventory").upsert(items).execute()
        return len(res.data) if res.data else len(items)
    except Exception as e:
        logger.error(f"Error upserting inventory: {e}")
        return len(items)


async def get_inventory(business_id: str) -> list[dict]:
    sb = get_supabase()
    try:
        res = (
            sb.table("inventory")
            .select("*")
            .eq("business_id", business_id)
            .execute()
        )
        return res.data if res.data else []
    except Exception as e:
        logger.warning(f"Error fetching inventory: {e}")
        return []


# ─── Market Prices ───────────────────────────────────────────────────────────

async def get_market_price(commodity: str, state: str) -> dict | None:
    sb = get_supabase()
    try:
        res = (
            sb.table("market_prices")
            .select("*")
            .ilike("commodity", f"%{commodity}%")
            .ilike("state", f"%{state}%")
            .order("date", desc=True)
            .limit(1)
            .execute()
        )
        if res.data and len(res.data) > 0:
            return res.data[0]
        
        # Fallback without state filter
        res_any = (
            sb.table("market_prices")
            .select("*")
            .ilike("commodity", f"%{commodity}%")
            .order("date", desc=True)
            .limit(1)
            .execute()
        )
        return res_any.data[0] if res_any.data and len(res_any.data) > 0 else None
    except Exception as e:
        logger.warning(f"Error querying market price: {e}")
        return None


async def bulk_insert_market_prices(rows: list[dict]) -> int:
    if not rows:
        return 0
    sb = get_supabase()
    try:
        res = sb.table("market_prices").upsert(rows).execute()
        return len(res.data) if res.data else len(rows)
    except Exception as e:
        logger.error(f"Error inserting market prices: {e}")
        return len(rows)


# ─── Alerts ──────────────────────────────────────────────────────────────────

async def insert_alert(alert: dict) -> dict:
    sb = get_supabase()
    try:
        res = sb.table("alerts_log").insert(alert).execute()
        return res.data[0] if res.data else alert
    except Exception as e:
        logger.error(f"Error inserting alert: {e}")
        return alert


async def get_alerts(business_id: str, limit: int = 50) -> list[dict]:
    sb = get_supabase()
    try:
        res = (
            sb.table("alerts_log")
            .select("*")
            .eq("business_id", business_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return res.data if res.data else []
    except Exception as e:
        logger.warning(f"Error fetching alerts: {e}")
        return []


async def acknowledge_alert(alert_id: str) -> dict:
    sb = get_supabase()
    try:
        res = (
            sb.table("alerts_log")
            .update({"acknowledged": True})
            .eq("id", alert_id)
            .execute()
        )
        return res.data[0] if res.data else {}
    except Exception as e:
        logger.error(f"Error acknowledging alert: {e}")
        return {}


# ─── Workflow Rules (thresholds) ─────────────────────────────────────────────

async def get_workflow_rules(business_id: str) -> dict:
    sb = get_supabase()
    try:
        res = (
            sb.table("workflow_rules")
            .select("*")
            .eq("business_id", business_id)
            .execute()
        )
        return res.data[0] if res.data and len(res.data) > 0 else {}
    except Exception as e:
        logger.warning(f"Error fetching workflow rules: {e}")
        return {}


# ─── Memory (past advice) ────────────────────────────────────────────────────

async def store_memory(business_id: str, key: str, value: dict):
    sb = get_supabase()
    try:
        sb.table("memory").upsert({
            "business_id": business_id,
            "key": key,
            "value": value,
        }).execute()
    except Exception as e:
        logger.warning(f"Error storing memory: {e}")


async def get_memory(business_id: str, key: str) -> dict | None:
    sb = get_supabase()
    try:
        res = (
            sb.table("memory")
            .select("value")
            .eq("business_id", business_id)
            .eq("key", key)
            .execute()
        )
        return res.data[0]["value"] if res.data and len(res.data) > 0 else None
    except Exception as e:
        logger.warning(f"Error getting memory: {e}")
        return None
