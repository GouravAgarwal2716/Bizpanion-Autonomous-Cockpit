"""
Alerts router — CRUD for Action Feed.
"""
from fastapi import APIRouter, HTTPException, Query
from services import supabase_client as db

router = APIRouter()


@router.get("/{business_id}")
async def get_alerts(
    business_id: str,
    limit: int = Query(50, le=200),
):
    """Get all alerts for a business, newest first."""
    alerts = await db.get_alerts(business_id, limit=limit)
    return {"alerts": alerts, "total": len(alerts)}


@router.patch("/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str):
    """Mark an alert as acknowledged."""
    result = await db.acknowledge_alert(alert_id)
    return result


@router.get("/{business_id}/summary")
async def get_alerts_summary(business_id: str):
    """Quick summary for the Home/Pulse page metric cards."""
    alerts = await db.get_alerts(business_id, limit=200)
    
    unacknowledged = [a for a in alerts if not a.get("acknowledged")]
    high_severity = [a for a in unacknowledged if a.get("severity") == "high"]
    whatsapp_sent = [a for a in alerts if a.get("whatsapp_sent")]

    return {
        "total_alerts": len(alerts),
        "unacknowledged": len(unacknowledged),
        "high_severity": len(high_severity),
        "whatsapp_sent": len(whatsapp_sent),
    }


from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

class WhatsAppDispatchRequest(BaseModel):
    phone_number: str
    business_name: str | None = None
    message: str | None = None

@router.post("/dispatch-whatsapp")
async def dispatch_whatsapp_direct(req: WhatsAppDispatchRequest):
    from services.twilio_service import send_whatsapp_alert
    target_phone = req.phone_number or "9518948695"
    biz_name = req.business_name or "Gourav Clothing Store"
    
    msg_body = req.message or (
        f"📑 *Bizpanion Autonomous Executive PDF Report*\n\n"
        f"Enterprise: *{biz_name}*\n"
        f"📅 Statement Date: *September 2026*\n\n"
        f"📈 *Key Financial Performance*:\n"
        f"• Total Turnover: *₹16,41,657*\n"
        f"• Net Operating Cash: *₹4,28,000*\n"
        f"• Runway Safety Buffer: *14 Days*\n"
        f"• Active Stockout Risk: *4 SKUs Flagged*\n\n"
        f"🔍 *Mandi Parity & Sector Intelligence*:\n"
        f"• Matched Sector: *Textiles & Garments*\n"
        f"• Top SKU: *Chanderi Cotton Saree (100% Weave)*\n"
        f"• Margin Variance: *-4.6% Below Parity*\n\n"
        f"🤖 *Featherless AI Strategic Guidance*:\n"
        f"\"Reinvest 15% working capital into high-velocity denim fabric to maximize PM MITRA subsidy eligibility.\"\n\n"
        f"📲 Access & Download Full PDF Report in Cockpit: http://localhost:3000/reports\n\n"
        f"_Bizpanion Autonomous Cockpit — Powered by Featherless AI_"
    )
    try:
        sid = send_whatsapp_alert(target_phone, msg_body)
        return {"status": "success", "sid": sid, "phone": target_phone}
    except Exception as e:
        logger.error(f"Direct WhatsApp dispatch error: {e}")
        return {"status": "skipped", "reason": str(e), "phone": target_phone}
