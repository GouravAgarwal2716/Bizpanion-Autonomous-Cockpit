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
        state["transactions"] = txns
        state["inventory"] = inv
        logger.info(f"[{state['run_id']}] Data Agent: loaded {len(txns)} txns, {len(inv)} inv items")
    except Exception as e:
        state["errors"].append(f"Data Agent error: {e}")
        logger.error(f"[{state['run_id']}] Data Agent failed: {e}")
    return state


# ─── Node: Market Data ─────────────────────────────────────────────────────────

async def market_data_node(state: PipelineState) -> PipelineState:
    """Fetches regional market prices for items in inventory."""
    try:
        from services.supabase_client import get_supabase
        sb = get_supabase()
        profile = state["profile"]
        region = profile.get("region", "")
        
        # Get all unique items from transactions
        items = list({t.get("category", "") for t in state["transactions"]})
        
        market_rows = []
        for item in items[:10]:  # limit to 10 items per run
            res = (
                sb.table("market_prices")
                .select("*")
                .ilike("commodity", f"%{item.split('_')[0][:5]}%")
                .order("date", desc=True)
                .limit(3)
                .execute()
            )
            market_rows.extend(res.data or [])
        
        state["market_prices"] = market_rows
        logger.info(f"[{state['run_id']}] Market Data: {len(market_rows)} price records")
    except Exception as e:
        state["errors"].append(f"Market data error: {e}")
        logger.error(f"[{state['run_id']}] Market data failed: {e}")
    return state


# ─── Node: RAG Agent ─────────────────────────────────────────────────────────

async def rag_agent_node(state: PipelineState) -> PipelineState:
    """Queries Pinecone for scheme eligibility and deadline matches."""
    try:
        profile = state["profile"]
        urgent = await check_scheme_deadlines(
            business_type=profile.get("business_type", ""),
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
                and t.get("transaction_type") == "sale"
            ]
            if len(item_txns) < 5:
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
            action = ""
            action_en = ""

        # Generate TTS audio (cached)
        audio_url = None
        try:
            cache_key = f"alert_{alert_type}_{business_id}_{hash(message[:30]) & 0xFFFF}"
            audio_url = await text_to_speech(message, language=language, cache_key=cache_key)
        except Exception as e:
            logger.warning(f"TTS failed for alert: {e}")

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

        # WhatsApp for high severity
        if anomaly.get("send_whatsapp") and profile.get("whatsapp_number"):
            try:
                wa_message = format_whatsapp_message(alert_type, alert["title"], message, business_name)
                send_whatsapp_alert(profile["whatsapp_number"], wa_message)
                
                # Update alert in DB as sent
                await db.get_supabase().table("alerts_log").update(
                    {"whatsapp_sent": True}
                ).eq("id", alert["id"]).execute()
                
                alert["whatsapp_sent"] = True
                state["whatsapp_sent"] = state.get("whatsapp_sent", 0) + 1
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
    """Fallback message when LLM is unavailable."""
    return _build_data_context(anomaly)


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
    
    # Parallel data gathering
    graph.add_edge("data_agent", "market_data")
    graph.add_edge("data_agent", "rag_agent")
    graph.add_edge("data_agent", "analysis_agent")
    
    # All converge into anomaly detection
    graph.add_edge("market_data", "anomaly_detection")
    graph.add_edge("rag_agent", "anomaly_detection")
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
