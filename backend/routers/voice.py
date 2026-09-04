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


# ─── Continuous Voice Mode / Gemini Live Style Companion ──────────────────────

class VoiceSessionStartRequest(BaseModel):
    business_id: str
    language: Language = Language.ENGLISH
    session_title: str | None = None


class VoiceTurnRequest(BaseModel):
    session_id: str
    business_id: str
    user_speech: str
    language: Language = Language.ENGLISH


@router.post("/session/start")
async def start_voice_session(req: VoiceSessionStartRequest):
    """
    Start a live continuous voice conversation session.
    Generates a welcome greeting based on real business metrics.
    """
    profile = await db.get_business_profile(req.business_id)
    if not profile:
        raise HTTPException(404, "Business profile not found")

    language = Language(profile.get("language", req.language.value))
    business_name = profile.get("business_name", "your business")
    
    # Context
    alerts = await db.get_alerts(req.business_id, limit=5)
    unack = [a for a in alerts if not a.get("acknowledged")]
    
    welcome_prompt = f"""
You are the voice companion for {business_name}, a micro-enterprise.
You are speaking live to the business owner in a voice session.
Current alerts waiting: {len(unack)}.
Give a warm, natural 2-sentence spoken welcome greeting, asking what they want to review today (sales, market prices, or government schemes).
Keep it conversational and brief.
"""
    welcome_text = await call_llm(welcome_prompt, language=language, max_tokens=80)
    audio_url = await text_to_speech(welcome_text, language=language)

    # Save session to Supabase
    sb = db.get_supabase()
    session_data = {
        "business_id": req.business_id,
        "session_title": req.session_title or f"Live Voice Session — {business_name}",
        "language": language.value,
        "messages": [
            {
                "role": "assistant",
                "text": welcome_text,
                "audio_url": audio_url,
                "timestamp": datetime.now().isoformat(),
            }
        ],
        "action_items": [],
    }
    
    try:
        res = sb.table("voice_sessions").insert(session_data).execute()
        session_obj = res.data[0] if res.data else session_data
        session_id = session_obj.get("id", "temp-session")
    except Exception as e:
        session_id = f"sess_{int(datetime.now().timestamp())}"
        session_obj = {**session_data, "id": session_id}

    return {
        "session_id": session_id,
        "welcome_text": welcome_text,
        "audio_url": audio_url,
        "language": language.value,
    }


@router.post("/session/turn")
async def voice_session_turn(req: VoiceTurnRequest):
    """
    Process a live voice turn:
    User speaks -> LLM reasons over business data + RAG -> Returns spoken voice + stores in long-term memory.
    """
    profile = await db.get_business_profile(req.business_id)
    language = Language(profile.get("language", req.language.value) if profile else req.language.value)
    
    # 1. Fetch live business context
    transactions = await db.get_transactions(req.business_id, limit=30)
    alerts = await db.get_alerts(req.business_id, limit=5)
    unack = [a for a in alerts if not a.get("acknowledged")]
    
    # 2. Check for RAG schemes relevant to user's question
    from agents.rag_agent import query_schemes
    schemes = await query_schemes(req.user_speech, business_type=profile.get("business_type", "all") if profile else "all", top_k=2)
    scheme_ctx = "\n".join([f"- {s.get('scheme_name')}: {s.get('benefit')}" for s in schemes])

    # 3. Construct Conversational Voice Prompt
    system_prompt = f"""
You are the voice business companion for {profile.get('business_name', 'the business')}.
You are speaking live to the business owner.
Rules:
1. Speak naturally, warmly, and concisely as if speaking in a live phone call.
2. Limit response to 2-3 short, spoken sentences. Avoid bullet points or special formatting since this will be read aloud.
3. Use the user's business context:
   - Unacknowledged alerts: {len(unack)}
   - Matched government subsidies/schemes: {scheme_ctx}
4. Always give practical, encouraging business guidance in the user's selected language ({language.value}).
"""

    prompt = f"User said: {req.user_speech}\nRespond as their spoken business companion."
    
    assistant_text = await call_llm(prompt, language=language, system_override=system_prompt, max_tokens=150)
    audio_url = await text_to_speech(assistant_text, language=language)

    # 4. Save turn to database for long-term memory
    sb = db.get_supabase()
    try:
        existing = sb.table("voice_sessions").select("*").eq("id", req.session_id).single().execute()
        if existing.data:
            msgs = existing.data.get("messages", [])
            msgs.append({"role": "user", "text": req.user_speech, "timestamp": datetime.now().isoformat()})
            msgs.append({"role": "assistant", "text": assistant_text, "audio_url": audio_url, "timestamp": datetime.now().isoformat()})
            sb.table("voice_sessions").update({"messages": msgs, "updated_at": datetime.now().isoformat()}).eq("id", req.session_id).execute()
    except Exception as e:
        logger.warning(f"Failed to persist voice turn to DB: {e}")

    return {
        "session_id": req.session_id,
        "assistant_text": assistant_text,
        "audio_url": audio_url,
        "language": language.value,
        "matched_schemes": schemes,
    }


@router.get("/sessions/{business_id}")
async def get_voice_sessions(business_id: str):
    """List past voice advisory sessions with transcript history."""
    sb = db.get_supabase()
    try:
        res = sb.table("voice_sessions").select("*").eq("business_id", business_id).order("created_at", desc=True).limit(20).execute()
        return res.data or []
    except Exception:
        return []

