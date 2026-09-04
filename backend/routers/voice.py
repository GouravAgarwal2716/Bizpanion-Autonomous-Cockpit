"""
Voice/TTS router.
Generates audio for the daily briefing and individual action card alerts.
"""
import asyncio
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.featherless import text_to_speech, call_llm, LANGUAGE_SYSTEM_PROMPTS
from services import supabase_client as db
from models.schemas import Language

router = APIRouter()


class BriefingRequest(BaseModel):
    business_id: str
    language: Language = Language.ENGLISH


@router.post("/briefing")
async def generate_daily_briefing(req: BriefingRequest):
    """
    Generate the "Play Today's Briefing" audio for the Home page.
    Summarizes today's key metrics and top alert in the user's language.
    """
    profile = await db.get_business_profile(req.business_id)
    if not profile:
        raise HTTPException(404, "Business profile not found")

    # Gather context
    alerts = await db.get_alerts(req.business_id, limit=10)
    unack = [a for a in alerts if not a.get("acknowledged")]
    
    # Pull today's transactions summary
    transactions = await db.get_transactions(req.business_id, limit=100)

    import pandas as pd
    from datetime import datetime, timedelta
    df = pd.DataFrame(transactions) if transactions else pd.DataFrame()
    
    today_sales = 0
    if not df.empty and "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        today = datetime.now().date()
        today_df = df[df["date"].dt.date == today]
        today_sales = today_df["total_amount"].sum() if not today_df.empty else 0

    business_name = profile.get("business_name", "your business")
    
    # Build briefing prompt
    top_alert = unack[0] if unack else None
    alert_summary = ""
    if top_alert:
        alert_summary = f"Top alert: {top_alert.get('message_en', top_alert.get('message', ''))}"

    prompt = f"""
Write a short, friendly 3-sentence voice briefing for {business_name}.
Today's sales so far: ₹{today_sales:.0f}.
You have {len(unack)} unacknowledged alerts.
{alert_summary}

The briefing should: greet by business name, state today's sales, mention the most important alert if any, and end with an encouraging note.
Keep it under 60 words. Speak naturally as if you are a helpful assistant.
"""
    
    language = Language(profile.get("language", req.language.value))
    
    briefing_text = await call_llm(prompt, language=language, max_tokens=100)
    
    cache_key = f"briefing_{req.business_id}_{datetime.now().strftime('%Y%m%d')}"
    audio_url = await text_to_speech(briefing_text, language=language, cache_key=cache_key)

    return {
        "text": briefing_text,
        "audio_url": audio_url,
        "language": language.value,
    }


class TTSRequest(BaseModel):
    text: str
    language: Language
    cache_key: str | None = None


@router.post("/tts")
async def generate_tts(req: TTSRequest):
    """Generate TTS for any text — used for inline Action Card audio."""
    audio_url = await text_to_speech(req.text, req.language, req.cache_key)
    return {"audio_url": audio_url, "language": req.language.value}


@router.get("/alert/{alert_id}/audio")
async def get_alert_audio(alert_id: str):
    """Get or generate audio for a specific alert."""
    sb = db.get_supabase()
    res = sb.table("alerts_log").select("*").eq("id", alert_id).single().execute()
    if not res.data:
        raise HTTPException(404, "Alert not found")
    
    alert = res.data
    if alert.get("audio_url"):
        return {"audio_url": alert["audio_url"]}
    
    # Generate on demand
    profile = await db.get_business_profile(alert["business_id"])
    language = Language(profile.get("language", "en") if profile else "en")
    
    message = alert.get("message") or alert.get("message_en", "")
    audio_url = await text_to_speech(message, language, cache_key=f"alert_{alert_id}")
    
    # Cache in DB
    sb.table("alerts_log").update({"audio_url": audio_url}).eq("id", alert_id).execute()
    
    return {"audio_url": audio_url}
