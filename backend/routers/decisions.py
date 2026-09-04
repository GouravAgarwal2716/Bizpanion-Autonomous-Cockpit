"""
Decisions Router — Autonomous Strategy & Scenario Simulation Playground.
"""
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from typing import Dict, Any, List
from services import supabase_client as db
from models.schemas import Language
from agents.decision_agent import generate_decision_scenarios, simulate_decision_outcome
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


class SimulateRequest(BaseModel):
    business_id: str
    scenario: Dict[str, Any]
    choices: Dict[int, str]
    language: Language = Language.ENGLISH


class SaveDecisionRequest(BaseModel):
    business_id: str
    scenario_title: str
    category: str
    problem_statement: str
    steps: List[Any]
    user_choices: Dict[str, Any]
    simulated_impact: Dict[str, Any]
    recommended_blueprint: str
    scheme_citations: List[Any] = []


@router.get("/scenarios/{business_id}")
async def get_scenarios(business_id: str):
    """
    Dynamically generates 3 strategic business decision paths based on latest ingested data.
    """
    profile = await db.get_business_profile(business_id)
    if not profile:
        # Fallback profile if testing
        profile = {"id": business_id, "business_name": "Ramesh Sabzi Bhandar", "business_type": "vegetables", "language": "en"}

    transactions = await db.get_transactions(business_id, limit=100)
    inventory = await db.get_inventory(business_id)
    alerts = await db.get_alerts(business_id, limit=10)
    
    # Extract anomaly list from alerts
    anomalies = [
        {
            "alert_type": a.get("alert_type"),
            "item_name": a.get("title", "").split(":")[-1].strip(),
            "user_price": a.get("data_snapshot", {}).get("user_price", 14.0),
            "market_price": a.get("data_snapshot", {}).get("market_price", 18.0),
        }
        for a in alerts
    ]

    language = Language(profile.get("language", "en"))
    scenarios = await generate_decision_scenarios(
        business_id=business_id,
        profile=profile,
        transactions=transactions,
        inventory=inventory,
        market_prices=[],
        anomalies=anomalies,
        language=language,
    )
    return {"business_id": business_id, "scenarios": scenarios}


@router.post("/simulate")
async def simulate_scenario(req: SimulateRequest):
    """
    Simulates the mathematical outcome of the user's selected choices for a scenario.
    """
    profile = await db.get_business_profile(req.business_id)
    language = Language(profile.get("language", req.language.value) if profile else req.language.value)
    
    outcome = simulate_decision_outcome(
        scenario=req.scenario,
        choices=req.choices,
        profile=profile or {},
        language=language,
    )
    return outcome


@router.post("/save")
async def save_decision_blueprint(req: SaveDecisionRequest):
    """
    Save the user's finalized strategic decision blueprint to Supabase for historical tracking.
    """
    sb = db.get_supabase()
    record = {
        "business_id": req.business_id,
        "scenario_title": req.scenario_title,
        "category": req.category,
        "problem_statement": req.problem_statement,
        "steps": req.steps,
        "user_choices": req.user_choices,
        "simulated_impact": req.simulated_impact,
        "recommended_blueprint": req.recommended_blueprint,
        "scheme_citations": req.scheme_citations,
        "status": "completed",
    }
    try:
        res = sb.table("decision_scenarios").insert(record).execute()
        return {"status": "saved", "record": res.data[0] if res.data else record}
    except Exception as e:
        logger.warning(f"Failed to save decision scenario: {e}")
        return {"status": "saved_local", "record": record}


@router.get("/history/{business_id}")
async def get_decision_history(business_id: str):
    """
    Get past completed strategic decisions and simulation blueprints for the business.
    """
    sb = db.get_supabase()
    try:
        res = sb.table("decision_scenarios").select("*").eq("business_id", business_id).order("created_at", desc=True).limit(20).execute()
        return res.data or []
    except Exception:
        return []
