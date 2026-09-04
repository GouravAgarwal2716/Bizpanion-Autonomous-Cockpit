"""
Market prices router — serves cached Agmarknet data and provides price lookup.
"""
from fastapi import APIRouter, Query
from services import supabase_client as db

router = APIRouter()


@router.get("/price")
async def get_market_price(
    commodity: str = Query(...),
    state: str = Query(""),
):
    """Get the latest market price for a commodity."""
    price = await db.get_market_price(commodity, state)
    if not price:
        return {"found": False, "commodity": commodity}
    return {"found": True, **price}


@router.get("/commodities")
async def list_commodities():
    """List all commodities available in the market_prices table."""
    sb = db.get_supabase()
    res = sb.table("market_prices").select("commodity").execute()
    commodities = list(set(r["commodity"] for r in (res.data or [])))
    return {"commodities": sorted(commodities)}
