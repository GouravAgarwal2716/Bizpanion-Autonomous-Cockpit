"""
Agents router — triggers the LangGraph pipeline manually or on schedule.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from agents.pipeline import run_pipeline

router = APIRouter()


class AgentRunRequest(BaseModel):
    business_id: str
    trigger: str = "manual"


@router.post("/run")
async def run_agents(req: AgentRunRequest):
    """Manually trigger the full agent pipeline for a business."""
    result = await run_pipeline(req.business_id, req.trigger)
    return result


@router.get("/health")
async def agents_health():
    return {"status": "ready", "pipeline": "langgraph"}
