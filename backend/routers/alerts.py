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
        "by_type": {
            "underpricing": len([a for a in unacknowledged if a.get("alert_type") == "underpricing"]),
            "stock_depletion": len([a for a in unacknowledged if a.get("alert_type") == "stock_depletion"]),
            "scheme_deadline": len([a for a in unacknowledged if a.get("alert_type") == "scheme_deadline"]),
            "sales_anomaly": len([a for a in unacknowledged if a.get("alert_type") == "sales_anomaly"]),
        },
    }
