"""
Tally Prime integration.
Tally exposes a built-in HTTP server on port 9000.
We send XML request envelopes and parse the response.
This is the standard, documented Tally integration method.
"""
import httpx
import asyncio
from lxml import etree
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from services.csv_pipeline import run_pipeline
from services import supabase_client as db
from agents.pipeline import run_pipeline as run_agent_pipeline
from models.schemas import DataSource
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


TALLY_BASE_URL = "http://localhost:9000"  # Default Tally Prime HTTP port

# ─── XML Request Templates ───────────────────────────────────────────────────

def make_voucher_request(from_date: str, to_date: str, company_name: str = "") -> str:
    """Build the Tally XML request to export sales vouchers."""
    company_filter = f"<COMPANY>{company_name}</COMPANY>" if company_name else ""
    return f"""<ENVELOPE>
  <HEADER>
    <TALLYREQUEST>Export Data</TALLYREQUEST>
  </HEADER>
  <BODY>
    <EXPORTDATA>
      <REQUESTDESC>
        <REPORTNAME>Voucher Register</REPORTNAME>
        <STATICVARIABLES>
          <SVFROMDATE>{from_date}</SVFROMDATE>
          <SVTODATE>{to_date}</SVTODATE>
          <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
          {company_filter}
        </STATICVARIABLES>
      </REQUESTDESC>
    </EXPORTDATA>
  </BODY>
</ENVELOPE>"""


def make_stock_request(company_name: str = "") -> str:
    """Build the Tally XML request to export stock summary."""
    company_filter = f"<COMPANY>{company_name}</COMPANY>" if company_name else ""
    return f"""<ENVELOPE>
  <HEADER>
    <TALLYREQUEST>Export Data</TALLYREQUEST>
  </HEADER>
  <BODY>
    <EXPORTDATA>
      <REQUESTDESC>
        <REPORTNAME>Stock Summary</REPORTNAME>
        <STATICVARIABLES>
          <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
          {company_filter}
        </STATICVARIABLES>
      </REQUESTDESC>
    </EXPORTDATA>
  </BODY>
</ENVELOPE>"""


# ─── XML Parsers ─────────────────────────────────────────────────────────────

def parse_vouchers(xml_text: str) -> list[dict]:
    """Parse Tally voucher XML into transaction dicts."""
    transactions = []
    try:
        root = etree.fromstring(xml_text.encode("utf-8"))
        for voucher in root.iter("VOUCHER"):
            vtype = voucher.findtext("VOUCHERTYPENAME", "").strip().lower()
            if vtype not in ("sales", "purchase"):
                continue

            date_str = voucher.findtext("DATE", "")
            date = None
            if date_str:
                try:
                    date = datetime.strptime(date_str, "%Y%m%d")
                except ValueError:
                    pass

            for entry in voucher.iter("INVENTORYENTRIES.LIST"):
                item_name = entry.findtext("STOCKITEMNAME", "Unknown")
                qty_text = entry.findtext("ACTUALQTY", "0")
                # Tally qty format: "10 Kg" or "10.00 Nos"
                parts = qty_text.strip().split()
                qty = float(parts[0].replace(",", "")) if parts else 0
                unit = parts[1] if len(parts) > 1 else "nos"
                
                rate_text = entry.findtext("RATE", "0")
                # Format: "23.50/Kg"
                rate = float(rate_text.split("/")[0].replace(",", "")) if rate_text else 0
                
                amount_text = entry.findtext("AMOUNT", "0")
                amount = abs(float(amount_text.replace(",", ""))) if amount_text else qty * rate

                transactions.append({
                    "date": date.isoformat() if date else datetime.now().isoformat(),
                    "item_name": item_name,
                    "category": "",  # will be inferred in pipeline
                    "quantity": qty,
                    "unit": unit,
                    "selling_price_per_unit": rate,
                    "total_amount": amount,
                    "transaction_type": vtype,
                    "source": DataSource.TALLY.value,
                    "flagged": False,
                    "flag_reason": None,
                })
    except Exception as e:
        logger.error(f"Tally XML parse error: {e}")
    return transactions


def parse_stock(xml_text: str) -> list[dict]:
    """Parse Tally stock summary XML into inventory dicts."""
    inventory = []
    try:
        root = etree.fromstring(xml_text.encode("utf-8"))
        for item in root.iter("STOCKITEM"):
            name = item.findtext("NAME", "").strip()
            if not name:
                continue
            
            closing_text = item.findtext("CLOSINGBALANCE", "0")
            parts = closing_text.strip().split()
            qty = float(parts[0].replace(",", "")) if parts else 0
            unit = parts[1] if len(parts) > 1 else "nos"

            inventory.append({
                "item_name": name,
                "category": "",
                "current_stock": qty,
                "unit": unit,
                "reorder_level": max(qty * 0.2, 5),  # default: 20% of stock or 5
                "last_updated": datetime.now().isoformat(),
            })
    except Exception as e:
        logger.error(f"Tally stock XML parse error: {e}")
    return inventory


# ─── HTTP Client ─────────────────────────────────────────────────────────────

async def call_tally(xml_request: str, tally_url: str = TALLY_BASE_URL) -> str:
    """POST XML request to Tally's HTTP server and return response text."""
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            tally_url,
            content=xml_request.encode("utf-8"),
            headers={"Content-Type": "text/xml"},
        )
        response.raise_for_status()
        return response.text


# ─── Router Endpoints ─────────────────────────────────────────────────────────

class TallySyncRequest(BaseModel):
    business_id: str
    company_name: str = ""
    tally_url: str = TALLY_BASE_URL
    days_back: int = 30


@router.post("/check")
async def check_tally_connection(req: TallySyncRequest):
    """Check if Tally is running and accessible."""
    ping_xml = """<ENVELOPE><HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>
    <BODY><EXPORTDATA><REQUESTDESC><REPORTNAME>List of Companies</REPORTNAME></REQUESTDESC></EXPORTDATA></BODY></ENVELOPE>"""
    try:
        response = await call_tally(ping_xml, req.tally_url)
        if "<ENVELOPE>" in response:
            return {"status": "connected", "message": "Tally Prime is running"}
        return {"status": "error", "message": "Unexpected response from Tally"}
    except Exception as e:
        raise HTTPException(503, f"Cannot connect to Tally at {req.tally_url}: {str(e)}")


@router.post("/sync")
async def sync_from_tally(req: TallySyncRequest):
    """
    Pull vouchers and stock from Tally Prime and run through the same pipeline.
    """
    to_date = datetime.now()
    from_date = to_date - timedelta(days=req.days_back)
    
    from_str = from_date.strftime("%Y%m%d")
    to_str = to_date.strftime("%Y%m%d")

    # Fetch vouchers
    try:
        voucher_xml = make_voucher_request(from_str, to_str, req.company_name)
        voucher_response = await call_tally(voucher_xml, req.tally_url)
        transactions = parse_vouchers(voucher_response)
    except Exception as e:
        raise HTTPException(503, f"Tally voucher sync failed: {e}")

    # Fetch stock
    try:
        stock_xml = make_stock_request(req.company_name)
        stock_response = await call_tally(stock_xml, req.tally_url)
        inventory_items = parse_stock(stock_response)
    except Exception as e:
        logger.warning(f"Tally stock sync failed: {e}")
        inventory_items = []

    # Run same pipeline as CSV (category inference, validation)
    import uuid as _uuid
    import pandas as pd
    import io

    if transactions:
        df = pd.DataFrame(transactions)
        # Add business_id and generate IDs
        df["business_id"] = req.business_id
        df["id"] = [str(_uuid.uuid4()) for _ in range(len(df))]
        # Infer categories
        from services.csv_pipeline import infer_category
        df["category"] = df["item_name"].apply(infer_category)
        
        rows = df.to_dict("records")
        saved = await db.insert_transactions(rows)
    else:
        saved = 0

    # Upsert inventory
    if inventory_items:
        for item in inventory_items:
            item["business_id"] = req.business_id
            from services.csv_pipeline import infer_category
            item["category"] = infer_category(item["item_name"])
        await db.upsert_inventory(inventory_items)

    # Trigger agent pipeline
    agent_result = await run_agent_pipeline(req.business_id, trigger="tally_sync")

    return {
        "status": "success",
        "transactions_imported": saved,
        "inventory_items_updated": len(inventory_items),
        "alerts_generated": agent_result["alerts_generated"],
        "whatsapp_sent": agent_result["whatsapp_sent"],
    }


@router.post("/import-xml")
async def import_tally_xml(
    xml_content: str = Body(..., media_type="text/xml"),
    business_id: str = Body(...),
):
    """
    Accept manually exported Tally XML file content.
    For users who prefer to export from Tally and upload the file.
    """
    transactions = parse_vouchers(xml_content)
    inventory_items = parse_stock(xml_content)

    import uuid as _uuid
    import pandas as pd

    results = {"transactions": 0, "inventory": 0}

    if transactions:
        df = pd.DataFrame(transactions)
        df["business_id"] = business_id
        df["id"] = [str(_uuid.uuid4()) for _ in range(len(df))]
        from services.csv_pipeline import infer_category
        df["category"] = df["item_name"].apply(infer_category)
        results["transactions"] = await db.insert_transactions(df.to_dict("records"))

    if inventory_items:
        for item in inventory_items:
            item["business_id"] = business_id
            from services.csv_pipeline import infer_category
            item["category"] = infer_category(item["item_name"])
        await db.upsert_inventory(inventory_items)
        results["inventory"] = len(inventory_items)

    return {"status": "success", **results}
