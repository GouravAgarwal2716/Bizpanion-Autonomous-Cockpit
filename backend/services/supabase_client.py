"""
Supabase client — singleton pattern.
Uses service role key for backend operations (bypasses RLS).
"""
from supabase import create_client, Client
from config import settings

_client: Client | None = None


def get_supabase() -> Client:
    global _client
    if _client is None:
        _client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_ROLE_KEY,
        )
    return _client


def init_supabase():
    """Call on startup to eagerly initialize."""
    get_supabase()
    print("✅ Supabase connected")


# ─── Business Profile ────────────────────────────────────────────────────────

async def upsert_business_profile(profile: dict) -> dict:
    sb = get_supabase()
    res = sb.table("business_profile").upsert(profile).execute()
    return res.data[0]


async def get_business_profile(user_id: str) -> dict | None:
    sb = get_supabase()
    res = sb.table("business_profile").select("*").eq("user_id", user_id).single().execute()
    return res.data


# ─── Transactions ─────────────────────────────────────────────────────────────

async def insert_transactions(rows: list[dict]) -> int:
    sb = get_supabase()
    res = sb.table("transactions").insert(rows).execute()
    return len(res.data)


async def get_transactions(business_id: str, limit: int = 500) -> list[dict]:
    sb = get_supabase()
    res = (
        sb.table("transactions")
        .select("*")
        .eq("business_id", business_id)
        .order("date", desc=True)
        .limit(limit)
        .execute()
    )
    return res.data


# ─── Inventory ───────────────────────────────────────────────────────────────

async def upsert_inventory(items: list[dict]) -> int:
    sb = get_supabase()
    res = sb.table("inventory").upsert(items).execute()
    return len(res.data)


async def get_inventory(business_id: str) -> list[dict]:
    sb = get_supabase()
    res = (
        sb.table("inventory")
        .select("*")
        .eq("business_id", business_id)
        .execute()
    )
    return res.data


# ─── Market Prices ───────────────────────────────────────────────────────────

async def get_market_price(commodity: str, state: str) -> dict | None:
    sb = get_supabase()
    res = (
        sb.table("market_prices")
        .select("*")
        .ilike("commodity", f"%{commodity}%")
        .ilike("state", f"%{state}%")
        .order("date", desc=True)
        .limit(1)
        .execute()
    )
    return res.data[0] if res.data else None


async def bulk_insert_market_prices(rows: list[dict]) -> int:
    sb = get_supabase()
    res = sb.table("market_prices").upsert(rows).execute()
    return len(res.data)


# ─── Alerts ──────────────────────────────────────────────────────────────────

async def insert_alert(alert: dict) -> dict:
    sb = get_supabase()
    res = sb.table("alerts_log").insert(alert).execute()
    return res.data[0]


async def get_alerts(business_id: str, limit: int = 50) -> list[dict]:
    sb = get_supabase()
    res = (
        sb.table("alerts_log")
        .select("*")
        .eq("business_id", business_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return res.data


async def acknowledge_alert(alert_id: str) -> dict:
    sb = get_supabase()
    res = (
        sb.table("alerts_log")
        .update({"acknowledged": True})
        .eq("id", alert_id)
        .execute()
    )
    return res.data[0]


# ─── Workflow Rules (thresholds) ─────────────────────────────────────────────

async def get_workflow_rules(business_id: str) -> dict:
    sb = get_supabase()
    res = (
        sb.table("workflow_rules")
        .select("*")
        .eq("business_id", business_id)
        .single()
        .execute()
    )
    return res.data or {}


# ─── Memory (past advice) ────────────────────────────────────────────────────

async def store_memory(business_id: str, key: str, value: dict):
    sb = get_supabase()
    sb.table("memory").upsert({
        "business_id": business_id,
        "key": key,
        "value": value,
    }).execute()


async def get_memory(business_id: str, key: str) -> dict | None:
    sb = get_supabase()
    res = (
        sb.table("memory")
        .select("value")
        .eq("business_id", business_id)
        .eq("key", key)
        .single()
        .execute()
    )
    return res.data["value"] if res.data else None
