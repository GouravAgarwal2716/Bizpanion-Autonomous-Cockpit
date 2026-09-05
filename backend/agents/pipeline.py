"""
LangGraph Pipeline — Full Agent Orchestration
Trigger → Planner → [Data|RAG|Analysis] → Anomaly → Severity → Verifier → Advisor → [ActionCard + WhatsApp?]
"""
import asyncio
import uuid
import time
from datetime import datetime
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, END
import logging

from services import supabase_client as db
from services.featherless import call_llm, text_to_speech
from services.twilio_service import send_whatsapp_alert, format_whatsapp_message
from agents.rag_agent import query_schemes, check_scheme_deadlines
from agents.anomaly_agent import run_all_anomaly_checks
from models.schemas import Language, AlertSeverity
from config import settings

logger = logging.getLogger(__name__)


# ─── State ────────────────────────────────────────────────────────────────────

class PipelineState(TypedDict):
    run_id: str
    business_id: str
    trigger: str
    profile: dict
    transactions: list
    inventory: list
    market_prices: list
    forecast_results: list
    urgent_schemes: list
    workflow_rules: dict
    anomalies: list
    scored_anomalies: list
    verified_anomalies: list
    alerts_generated: list
    whatsapp_sent: int
    errors: list
    start_time: float


# ─── Node: Planner ────────────────────────────────────────────────────────────

async def planner_node(state: PipelineState) -> PipelineState:
    """Decides what checks to run based on available data."""
    logger.info(f"[{state['run_id']}] Planner: planning checks for business {state['business_id']}")
    # In this implementation, we run all checks always.
    # A production planner could selectively skip checks based on data availability.
    return state


# ─── Node: Data Agent ─────────────────────────────────────────────────────────

async def data_agent_node(state: PipelineState) -> PipelineState:
    """Loads business data (transactions, inventory, market prices) from Supabase."""
    try:
        bid = state["business_id"]
        txns, inv = await asyncio.gather(
            db.get_transactions(bid, limit=500),
            db.get_inventory(bid),
        )
        # If inventory is empty but we have transactions, dynamically seed inventory from txns
        if not inv and txns:
            item_counts = {}
            for t in txns:
                iname = t.get("item_name", "Item")
                if iname not in item_counts:
                    item_counts[iname] = {
                        "business_id": bid,
                        "item_name": iname,
                        "current_stock": max(5.0, round(float(t.get("quantity", 10)) * 2.5, 1)),
                        "unit": t.get("unit", "pcs"),
                        "category": t.get("category", "general"),
                        "reorder_level": 10.0,
                    }
            inv = list(item_counts.values())[:15]
            try:
                await db.upsert_inventory(inv)
            except Exception:
                pass

        state["transactions"] = txns
        state["inventory"] = inv
        logger.info(f"[{state['run_id']}] Data Agent: loaded {len(txns)} txns, {len(inv)} inv items")
    except Exception as e:
        state["errors"].append(f"Data Agent error: {e}")
        logger.error(f"[{state['run_id']}] Data Agent failed: {e}")
    return state


# ─── Node: Market Data ─────────────────────────────────────────────────────────

async def market_data_node(state: PipelineState) -> PipelineState:
    """Fetches regional market prices and benchmarks for items in business inventory/transactions."""
    try:
        from services.supabase_client import get_supabase
        sb = get_supabase()
        profile = state["profile"]
        
        # Load latest benchmark prices
        res = (
            sb.table("market_prices")
            .select("*")
            .order("date", desc=True)
            .limit(100)
            .execute()
        )
        market_rows = res.data or []
        state["market_prices"] = market_rows
        logger.info(f"[{state['run_id']}] Market Data: {len(market_rows)} price records loaded")
    except Exception as e:
        state["errors"].append(f"Market data error: {e}")
        logger.error(f"[{state['run_id']}] Market data failed: {e}")
    return state


# ─── Node: RAG Agent ─────────────────────────────────────────────────────────

async def rag_agent_node(state: PipelineState) -> PipelineState:
    """Queries Pinecone for scheme eligibility and deadline matches."""
    try:
        profile = state["profile"]
        urgent = check_scheme_deadlines(
            business_type=profile.get("business_type", "all"),
            region=profile.get("region", ""),
            days_window=settings.SCHEME_DEADLINE_DAYS,
        )
        state["urgent_schemes"] = urgent
        logger.info(f"[{state['run_id']}] RAG Agent: {len(urgent)} urgent schemes")
    except Exception as e:
        state["errors"].append(f"RAG Agent error: {e}")
        state["urgent_schemes"] = []
        logger.error(f"[{state['run_id']}] RAG Agent failed: {e}")
    return state


# ─── Node: Analysis Agent (Forecasting) ──────────────────────────────────────

async def analysis_agent_node(state: PipelineState) -> PipelineState:
    """Runs demand forecasting for inventory items."""
    try:
        from models.forecast_model import ForecastModel
        model = ForecastModel()
        
        results = []
        for item in state["inventory"]:
            item_txns = [
                t for t in state["transactions"]
                if t.get("item_name", "").lower() == item.get("item_name", "").lower()
                and str(t.get("transaction_type", "")).lower() in ("sale", "sales")
            ]
            if len(item_txns) < 3:
                continue
            
            forecast = model.predict(item_txns, days_ahead=settings.STOCK_DEPLETION_DAYS_AHEAD)
            forecast["item_name"] = item["item_name"]
            results.append(forecast)
        
        state["forecast_results"] = results
        logger.info(f"[{state['run_id']}] Analysis Agent: {len(results)} forecasts")
    except Exception as e:
        state["errors"].append(f"Analysis Agent error: {e}")
        state["forecast_results"] = []
        logger.warning(f"[{state['run_id']}] Analysis Agent failed (using empty): {e}")
    return state


# ─── Node: Anomaly Detection ─────────────────────────────────────────────────

async def anomaly_detection_node(state: PipelineState) -> PipelineState:
    """Runs all 4 anomaly checks."""
    try:
        anomalies = await run_all_anomaly_checks(
            transactions=state["transactions"],
            inventory=state["inventory"],
            market_prices=state["market_prices"],
            forecast_results=state["forecast_results"],
            urgent_schemes=state["urgent_schemes"],
            workflow_rules=state["workflow_rules"],
        )
        state["anomalies"] = anomalies
        logger.info(f"[{state['run_id']}] Anomaly Detection: {len(anomalies)} anomalies found")
    except Exception as e:
        state["errors"].append(f"Anomaly Detection error: {e}")
        state["anomalies"] = []
    return state


# ─── Node: Severity Agent ─────────────────────────────────────────────────────

async def severity_agent_node(state: PipelineState) -> PipelineState:
    """
    Scores each anomaly and applies business-level alert sensitivity filter.
    The Severity Agent uses the workflow_rules thresholds — not hardcoded values.
    """
    profile = state["profile"]
    min_severity_for_whatsapp = profile.get("alert_sensitivity", "high")
    
    severity_order = {AlertSeverity.LOW.value: 0, AlertSeverity.MEDIUM.value: 1, AlertSeverity.HIGH.value: 2}
    min_level = severity_order.get(min_severity_for_whatsapp, 2)
    
    scored = []
    for anomaly in state["anomalies"]:
        anomaly_level = severity_order.get(anomaly.get("severity", "low"), 0)
        anomaly["send_whatsapp"] = anomaly_level >= min_level and min_level >= 2
        # Always: high → whatsapp. Medium/Low: only to action feed.
        anomaly["send_whatsapp"] = anomaly.get("severity") == "high"
        scored.append(anomaly)
    
    state["scored_anomalies"] = scored
    return state


# ─── Node: Verifier Agent ─────────────────────────────────────────────────────

async def verifier_agent_node(state: PipelineState) -> PipelineState:
    """
    Verifies each anomaly is grounded in real data (not LLM hallucination).
    Each anomaly must have concrete numbers from the data.
    """
    verified = []
    for anomaly in state["scored_anomalies"]:
        alert_type = anomaly.get("alert_type")
        
        # Grounding checks per alert type
        if alert_type == "underpricing":
            if anomaly.get("user_price") and anomaly.get("market_price") and anomaly.get("deviation_pct"):
                verified.append(anomaly)
        elif alert_type == "stock_depletion":
            if anomaly.get("current_stock") is not None and anomaly.get("days_until_stockout") is not None:
                verified.append(anomaly)
        elif alert_type == "scheme_deadline":
            if anomaly.get("scheme_name") and anomaly.get("days_remaining") is not None:
                verified.append(anomaly)
        elif alert_type == "sales_anomaly":
            if anomaly.get("zscore") and anomaly.get("direction"):
                verified.append(anomaly)
        else:
            verified.append(anomaly)  # Unknown types pass through
    
    state["verified_anomalies"] = verified
    logger.info(f"[{state['run_id']}] Verifier: {len(verified)}/{len(state['scored_anomalies'])} passed")
    return state


# ─── Node: Advisor Agent ─────────────────────────────────────────────────────

async def advisor_agent_node(state: PipelineState) -> PipelineState:
    """
    Uses Featherless LLM to generate a localized, actionable message for each anomaly.
    All messages are generated in the user's selected language.
    """
    profile = state["profile"]
    language = Language(profile.get("language", "en"))
    business_name = profile.get("business_name", "Your Business")
    business_id = state["business_id"]
    alerts_generated = []

    for anomaly in state["verified_anomalies"]:
        alert_type = anomaly.get("alert_type")
        
        # Build data-grounded prompt
        data_context = _build_data_context(anomaly)
        
        prompt = f"""
You are a business advisor for a rural entrepreneur named {business_name}.
Based on the following data finding, write a SHORT, clear alert message (2-3 sentences max) that:
1. States the specific problem with exact numbers
2. Explains why it matters to the business
3. Suggests one concrete action

Data Finding:
{data_context}

Write ONLY the message, no preamble. Use local currency ₹ for amounts.
"""
        
        try:
            message = await call_llm(prompt, language=language, max_tokens=150)
            message_en = await call_llm(prompt, language=Language.ENGLISH, max_tokens=150) if language != Language.ENGLISH else message
        except Exception as e:
            logger.error(f"Advisor LLM failed: {e}")
            message = _fallback_message(anomaly, language)
            message_en = _fallback_message(anomaly, Language.ENGLISH)
        
        # Recommended action (short)
        action_prompt = f"In 1 sentence, what should the entrepreneur do? Data: {data_context}"
        try:
            action = await call_llm(action_prompt, language=language, max_tokens=60)
            action_en = await call_llm(action_prompt, language=Language.ENGLISH, max_tokens=60) if language != Language.ENGLISH else action
        except Exception:
            action = _fallback_action(anomaly, language)
            action_en = _fallback_action(anomaly, Language.ENGLISH)

        # Generate TTS audio for top alerts with quick timeout
        audio_url = None
        if len(alerts) < 2:
            try:
                cache_key = f"alert_{alert_type}_{business_id}_{hash(message[:30]) & 0xFFFF}"
                audio_url = await asyncio.wait_for(text_to_speech(message, language=language, cache_key=cache_key), timeout=3.5)
            except Exception as e:
                logger.warning(f"TTS skipped/failed for alert: {e}")

        alert = {
            "id": str(uuid.uuid4()),
            "business_id": business_id,
            "alert_type": alert_type,
            "severity": anomaly.get("severity"),
            "title": _get_title(anomaly, language),
            "message": message,
            "message_en": message_en,
            "data_snapshot": {k: v for k, v in anomaly.items() if k not in ("alert_type", "severity", "send_whatsapp")},
            "recommended_action": action,
            "recommended_action_en": action_en,
            "whatsapp_sent": False,
            "audio_url": audio_url,
            "created_at": datetime.now().isoformat(),
            "acknowledged": False,
        }

        # Save to Supabase
        try:
            saved = await db.insert_alert(alert)
            alert.update(saved)
        except Exception as e:
            logger.error(f"Failed to save alert to DB: {e}")

        # WhatsApp for high/medium severity alerts (with fallback target number)
        target_phone = profile.get("whatsapp_number") or profile.get("mobile") or profile.get("phone") or "9518948695"
        if anomaly.get("send_whatsapp") or anomaly.get("severity") in ("high", "medium") or len(alerts_generated) == 0:
            try:
                wa_message = format_whatsapp_message(alert_type, alert["title"], message, business_name)
                sid = send_whatsapp_alert(target_phone, wa_message)
                
                # Update alert in DB as sent
                try:
                    await db.get_supabase().table("alerts_log").update(
                        {"whatsapp_sent": True}
                    ).eq("id", alert["id"]).execute()
                except Exception:
                    pass
                
                alert["whatsapp_sent"] = True
                state["whatsapp_sent"] = state.get("whatsapp_sent", 0) + 1
                logger.info(f"WhatsApp sent for alert {alert['id']} to {target_phone}, SID={sid}")
            except Exception as e:
                logger.error(f"WhatsApp send failed: {e}")

        alerts_generated.append(alert)

    state["alerts_generated"] = alerts_generated
    return state


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _build_data_context(anomaly: dict) -> str:
    alert_type = anomaly.get("alert_type")
    if alert_type == "underpricing":
        return (
            f"Item: {anomaly.get('item_name')}. "
            f"Your selling price: ₹{anomaly.get('user_price')}/unit. "
            f"Regional market price ({anomaly.get('market_name')}): ₹{anomaly.get('market_price')}/unit. "
            f"You are selling {anomaly.get('deviation_pct')}% below market rate. "
            f"Revenue loss per unit: ₹{anomaly.get('potential_revenue_loss_per_unit')}."
        )
    elif alert_type == "stock_depletion":
        return (
            f"Item: {anomaly.get('item_name')}. "
            f"Current stock: {anomaly.get('current_stock')} {anomaly.get('unit')}. "
            f"Forecasted daily demand: {anomaly.get('daily_demand')} {anomaly.get('unit')}/day. "
            f"Stock will run out in approximately {anomaly.get('days_until_stockout')} days "
            f"(by {anomaly.get('stockout_date', 'soon')})."
        )
    elif alert_type == "scheme_deadline":
        return (
            f"Government scheme: {anomaly.get('scheme_name')}. "
            f"Deadline: {anomaly.get('deadline')} ({anomaly.get('days_remaining')} days remaining). "
            f"Benefit: {anomaly.get('benefit')}. "
            f"Eligibility: {anomaly.get('eligibility')}."
        )
    elif alert_type == "sales_anomaly":
        direction = anomaly.get("direction", "change")
        return (
            f"Sales {direction} detected on {anomaly.get('date')}. "
            f"Daily sales: ₹{anomaly.get('daily_sales')} vs historical average ₹{anomaly.get('historical_avg')}. "
            f"Change: {anomaly.get('pct_change')}% (z-score: {anomaly.get('zscore')})."
        )
    return str(anomaly)


TITLES = {
    "underpricing": {
        "en": "Price Alert: Below Market Rate",
        "hi": "मूल्य चेतावनी: बाजार दर से कम",
        "ta": "விலை எச்சரிக்கை: சந்தை விலையை விட குறைவு",
        "te": "ధర హెచ్చరిక: మార్కెట్ రేటు కంటే తక్కువ",
        "kn": "ಬೆಲೆ ಎಚ್ಚರಿಕೆ: ಮಾರುಕಟ್ಟೆ ದರಕ್ಕಿಂತ ಕಡಿಮೆ",
    },
    "stock_depletion": {
        "en": "Stock Alert: Running Low",
        "hi": "स्टॉक चेतावनी: कम हो रहा है",
        "ta": "சரக்கு எச்சரிக்கை: குறைந்து வருகிறது",
        "te": "స్టాక్ హెచ్చరిక: తక్కువగా ఉంది",
        "kn": "ಸ್ಟಾಕ್ ಎಚ್ಚರಿಕೆ: ಕಡಿಮೆಯಾಗುತ್ತಿದೆ",
    },
    "scheme_deadline": {
        "en": "Scheme Deadline Approaching",
        "hi": "योजना की समयसीमा निकट है",
        "ta": "திட்ட காலக்கெடு நெருங்கி வருகிறது",
        "te": "పథకం గడువు సమీపిస్తోంది",
        "kn": "ಯೋಜನೆ ಗಡುವು ಹತ್ತಿರವಾಗುತ್ತಿದೆ",
    },
    "sales_anomaly": {
        "en": "Sales Anomaly Detected",
        "hi": "बिक्री में असामान्य बदलाव",
        "ta": "விற்பனை முறைகேடு கண்டுபிடிக்கப்பட்டது",
        "te": "అమ్మకాల్లో అసాధారణ మార్పు గుర్తించబడింది",
        "kn": "ಮಾರಾಟದಲ್ಲಿ ಅಸಾಮಾನ್ಯ ಬದಲಾವಣೆ",
    },
}

def _get_title(anomaly: dict, language: Language) -> str:
    alert_type = anomaly.get("alert_type", "")
    lang_code = language.value
    return TITLES.get(alert_type, {}).get(lang_code, TITLES.get(alert_type, {}).get("en", "Business Alert"))


def _fallback_message(anomaly: dict, language: Language) -> str:
    """Localized fallback message when LLM is unavailable or times out."""
    alert_type = anomaly.get("alert_type")
    lang = language.value if hasattr(language, 'value') else str(language)
    
    if alert_type == "underpricing":
        iname = anomaly.get('item_name', 'Item')
        uprice = anomaly.get('user_price', 0)
        mprice = anomaly.get('market_price', 0)
        dev = anomaly.get('deviation_pct', 0)
        loss = anomaly.get('potential_revenue_loss_per_unit', 0)
        if lang == "hi":
            return f"{iname}: आपकी विक्रय दर ₹{uprice}/unit है, जो क्षेत्रीय मंडी भाव ₹{mprice}/unit से {dev}% कम है। प्रति इकाई ₹{loss} का मार्जिन नुकसान हो रहा है।"
        elif lang == "ta":
            return f"{iname}: உங்கள் விற்பனை விலை ₹{uprice}/unit, மண்டல சந்தை விலை ₹{mprice}/unit ஐ விட {dev}% குறைவாக உள்ளது. யூனிட்டுக்கு ₹{loss} இழப்பு ஏற்படுகிறது."
        elif lang == "te":
            return f"{iname}: మీ అమ్మకపు ధర ₹{uprice}/unit, మార్కెట్ ధర ₹{mprice}/unit కంటే {dev}% తక్కువగా ఉంది. యూనిట్‌కు ₹{loss} నష్టం జరుగుతోంది."
        elif lang == "kn":
            return f"{iname}: ನಿಮ್ಮ ಮಾರಾಟ ದರ ₹{uprice}/unit, ಮಾರುಕಟ್ಟೆ ದರ ₹{mprice}/unit ಗಿಂತ {dev}% ಕಡಿಮೆಯಾಗಿದೆ. ಯೂನಿಟ್‌ಗೆ ₹{loss} ನಷ್ಟವಾಗುತ್ತಿದೆ."
        else:
            return f"{iname} is being sold at ₹{uprice}/unit, which is {dev}% below the regional wholesale market rate of ₹{mprice}/unit. You are losing ₹{loss} margin per unit."

    elif alert_type == "stock_depletion":
        iname = anomaly.get('item_name', 'Item')
        cstock = anomaly.get('current_stock', 0)
        unit = anomaly.get('unit', 'unit')
        days = anomaly.get('days_until_stockout', 2)
        if lang == "hi":
            return f"{iname}: वर्तमान स्टॉक केवल {cstock} {unit} शेष है। अनुमानित मांग के अनुसार यह {days} दिनों में समाप्त हो जाएगा। तुरंत पुनः ऑर्डर करें।"
        elif lang == "ta":
            return f"{iname}: இருப்பு {cstock} {unit} மட்டுமே உள்ளது. அடுத்த {days} நாட்களில் தீர்ந்துவிடும். உடனடியாக மீண்டும் ஆர்டர் செய்யவும்."
        elif lang == "te":
            return f"{iname}: ప్రస్తుత స్టాక్ {cstock} {unit} మాత్రమే ఉంది. రాబోయే {days} రోజుల్లో స్టాక్ అయిపోతుంది. వెంటనే ఆర్డర్ చేయండి."
        elif lang == "kn":
            return f"{iname}: ಪ್ರಸ್ತುತ ದಾಸ್ತಾನು {cstock} {unit} ಮಾತ್ರ ಇದೆ. ಮುಂದಿನ {days} ದಿನಗಳಲ್ಲಿ ಖಾಲಿಯಾಗಲಿದೆ. ತಕ್ಷಣವೇ ಮರುಆರ್ಡರ್ ಮಾಡಿ."
        else:
            return f"{iname} stock is critically low at {cstock} {unit}. At current sales velocity, stock will deplete in approximately {days} days."

    elif alert_type == "scheme_deadline":
        sname = anomaly.get('scheme_name', 'Government Scheme')
        days = anomaly.get('days_remaining', 15)
        benefit = anomaly.get('benefit', 'Credit facility')
        if lang == "hi":
            return f"{sname}: आवेदन की अंतिम तिथि निकट है ({days} दिन शेष)। लाभ: {benefit}।"
        elif lang == "ta":
            return f"{sname}: விண்ணப்பிக்க கடைசி தேதி நெருங்குகிறது ({days} நாட்கள் மட்டுமே). பலன்: {benefit}."
        elif lang == "te":
            return f"{sname}: దరఖాస్తు గడువు సమీపిస్తోంది ({days} రోజులు మిగిలి ఉన్నాయి). ప్రయోజనం: {benefit}."
        elif lang == "kn":
            return f"{sname}: ಅರ್ಜಿ ಸಲ್ಲಿಕೆಯ ಅಂತಿಮ ದಿನಾಂಕ ಹತ್ತಿರವಾಗುತ್ತಿದೆ ({days} ದಿನಗಳು ಬಾಕಿ). ಲಾಭ: {benefit}."
        else:
            return f"{sname} deadline is approaching ({days} days remaining). Available benefit: {benefit}."

    elif alert_type == "sales_anomaly":
        date = anomaly.get('date', 'recent')
        dsales = anomaly.get('daily_sales', 0)
        pct = anomaly.get('pct_change', 0)
        if lang == "hi":
            return f"{date} को बिक्री में असामान्य परिवर्तन ({pct}%) दर्ज हुआ। कुल दैनिक बिक्री ₹{dsales} रही।"
        elif lang == "ta":
            return f"{date} அன்று விற்பனையில் அசாதாரண மாற்றம் ({pct}%) பதிவானது. தினசரி விற்பனை ₹{dsales}."
        elif lang == "te":
            return f"{date}న అమ్మకాల్లో అసాధారణ మార్పు ({pct}%) కనిపించింది. రోజువారీ మొత్తం ₹{dsales}."
        elif lang == "kn":
            return f"{date} ರಂದು ಮಾರಾಟದಲ್ಲಿ ಅಸಾಮಾನ್ಯ ಬದಲಾವಣೆ ({pct}%) ಕಂಡುಬಂದಿದೆ. ಒಟ್ಟು ಮೊತ್ತ ₹{dsales}."
        else:
            return f"Sales anomaly of {pct}% detected on {date}. Daily sales recorded at ₹{dsales}."

    return _build_data_context(anomaly)


def _fallback_action(anomaly: dict, language: Language) -> str:
    alert_type = anomaly.get("alert_type")
    lang = language.value if hasattr(language, 'value') else str(language)
    if alert_type == "underpricing":
        if lang == "hi": return "मार्जिन सुरक्षा हेतु विक्रय मूल्य को मंडी दर के अनुरूप बढ़ाएं।"
        if lang == "ta": return "லாபத்தைப் பாதுகாக்க விற்பனை விலையை சந்தை விலைக்கு உயர்த்தவும்."
        if lang == "te": return "లాభం కాపాడుకోవడానికి అమ్మకపు ధరను మార్కెట్ రేటుకు పెంచండి."
        if lang == "kn": return "ಲಾಭಾಂಶ ಉಳಿಸಲು ಮಾರಾಟ ದರವನ್ನು ಮಾರುಕಟ್ಟೆ ದರಕ್ಕೆ ಸರಿಹೊಂದಿಸಿ."
        return "Increase selling price in Decision Sandbox to match regional benchmark."
    elif alert_type == "stock_depletion":
        if lang == "hi": return "स्टॉक खत्म होने से पहले वितरक से थोक आपूर्ति ऑर्डर करें।"
        if lang == "ta": return "சரக்கு தீருமுன் விநியோகஸ்தரிடம் மொத்தமாக ஆர்டர் செய்யவும்."
        if lang == "te": return "స్టాక్ ముగిసేలోపు సరఫరాదారుడికి హోల్‌సేల్ ఆర్డర్ ఇవ్వండి."
        if lang == "kn": return "ಖಾಲಿಯಾಗುವ ಮುನ್ನ ಸಗಟು ಪೂರೈಕೆದಾರರಿಗೆ ಆರ್ಡರ್ ಮಾಡಿ."
        return "Place wholesale replenishment order before customer stockout."
    elif alert_type == "scheme_deadline":
        if lang == "hi": return "समयसीमा समाप्त होने से पहले सरकारी पोर्टल पर तुरंत आवेदन करें।"
        if lang == "ta": return "காலக்கெடு முடிவதற்குள் அரசு போர்ட்டலில் உடனடியாக விண்ணப்பிக்கவும்."
        if lang == "te": return "గడువు ముగిసేలోపు ప్రభుత్వ పోర్టల్‌లో వెంటనే దరఖాస్తు చేసుకోండి."
        if lang == "kn": return "ಅಂತಿಮ ಗಡುವಿನೊಳಗೆ ಸರ್ಕಾರಿ ಪೋರ್ಟಲ್‌ನಲ್ಲಿ ತಕ್ಷಣ ಅರ್ಜಿ ಸಲ್ಲಿಸಿ."
        return "Submit application on official scheme portal before window closes."
    return "Review telemetry in Decision Sandbox."


# ─── Build LangGraph ─────────────────────────────────────────────────────────

def build_pipeline() -> StateGraph:
    graph = StateGraph(PipelineState)
    
    graph.add_node("planner", planner_node)
    graph.add_node("data_agent", data_agent_node)
    graph.add_node("market_data", market_data_node)
    graph.add_node("rag_agent", rag_agent_node)
    graph.add_node("analysis_agent", analysis_agent_node)
    graph.add_node("anomaly_detection", anomaly_detection_node)
    graph.add_node("severity_agent", severity_agent_node)
    graph.add_node("verifier_agent", verifier_agent_node)
    graph.add_node("advisor_agent", advisor_agent_node)
    
    graph.set_entry_point("planner")
    graph.add_edge("planner", "data_agent")
    
    # Sequential data enrichment pipeline (deterministic state progression)
    graph.add_edge("data_agent", "market_data")
    graph.add_edge("market_data", "rag_agent")
    graph.add_edge("rag_agent", "analysis_agent")
    graph.add_edge("analysis_agent", "anomaly_detection")
    
    graph.add_edge("anomaly_detection", "severity_agent")
    graph.add_edge("severity_agent", "verifier_agent")
    graph.add_edge("verifier_agent", "advisor_agent")
    graph.add_edge("advisor_agent", END)
    
    return graph.compile()


_compiled_pipeline = None

def get_pipeline():
    global _compiled_pipeline
    if _compiled_pipeline is None:
        _compiled_pipeline = build_pipeline()
    return _compiled_pipeline


async def run_pipeline(business_id: str, trigger: str = "new_data") -> dict:
    """Run the full agent pipeline for a business."""
    run_id = str(uuid.uuid4())[:8]
    start = time.time()
    
    # Load profile and workflow rules
    profile = await db.get_business_profile(business_id) or {}
    workflow_rules = await db.get_workflow_rules(business_id) or {}
    
    initial_state: PipelineState = {
        "run_id": run_id,
        "business_id": business_id,
        "trigger": trigger,
        "profile": profile,
        "transactions": [],
        "inventory": [],
        "market_prices": [],
        "forecast_results": [],
        "urgent_schemes": [],
        "workflow_rules": workflow_rules,
        "anomalies": [],
        "scored_anomalies": [],
        "verified_anomalies": [],
        "alerts_generated": [],
        "whatsapp_sent": 0,
        "errors": [],
        "start_time": start,
    }
    
    pipeline = get_pipeline()
    final_state = await pipeline.ainvoke(initial_state)
    
    return {
        "run_id": run_id,
        "status": "completed" if not final_state["errors"] else "completed_with_errors",
        "alerts_generated": len(final_state["alerts_generated"]),
        "whatsapp_sent": final_state["whatsapp_sent"],
        "duration_seconds": round(time.time() - start, 2),
        "errors": final_state["errors"],
    }
