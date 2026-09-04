"""
Upload router — CSV upload with real-time streaming progress via SSE.
"""
import asyncio
import json
import uuid
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse, Response
from services.csv_pipeline import run_pipeline, generate_cleaned_csv
from services import supabase_client as db
from models.schemas import DataSource
from agents.pipeline import run_pipeline as run_agent_pipeline
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# Temporary in-memory store for cleaned CSV bytes (keyed by upload_id)
_cleaned_csv_store: dict[str, bytes] = {}


@router.post("/csv")
async def upload_csv(
    file: UploadFile = File(...),
    business_id: str = Form(...),
):
    """
    Upload a CSV file and process it through the data pipeline.
    Returns SSE stream with live progress updates.
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(400, "Only .csv files accepted")

    file_bytes = await file.read()
    if len(file_bytes) > 10 * 1024 * 1024:  # 10 MB limit
        raise HTTPException(400, "File too large (max 10 MB)")

    upload_id = str(uuid.uuid4())

    async def event_stream():
        loop = asyncio.get_event_loop()
        results = None

        # Run pipeline in thread (it's a sync generator)
        import concurrent.futures
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)

        def run_sync():
            gen = run_pipeline(file_bytes, business_id, DataSource.CSV)
            steps = []
            try:
                while True:
                    step = next(gen)
                    steps.append(step)
            except StopIteration as e:
                return steps, e.value
            return steps, {}

        future = loop.run_in_executor(executor, run_sync)
        steps, final_result = await future

        # Yield each step as SSE
        for step in steps:
            data = json.dumps({
                "type": "step",
                "step": step.step,
                "status": step.status,
                "message": step.message,
                "detail": step.detail,
            })
            yield f"data: {data}\n\n"
            await asyncio.sleep(0.05)  # Tiny delay for visual effect

        # Write to Supabase
        transactions = final_result.get("transactions", [])
        if transactions:
            yield f"data: {json.dumps({'type': 'step', 'step': 'write', 'status': 'running', 'message': f'Writing {len(transactions)} rows to database...'})}\n\n"
            try:
                written = await db.insert_transactions(transactions)
                yield f"data: {json.dumps({'type': 'step', 'step': 'write', 'status': 'done', 'message': f'Saved {written} records to Supabase'})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'type': 'step', 'step': 'write', 'status': 'error', 'message': f'DB write failed: {str(e)}'})}\n\n"

        # Cache cleaned CSV
        csv_bytes = generate_cleaned_csv(final_result.get("transactions", []))
        _cleaned_csv_store[upload_id] = csv_bytes

        # Trigger agent pipeline
        yield f"data: {json.dumps({'type': 'step', 'step': 'agents', 'status': 'running', 'message': 'Running autonomous analysis agents...'})}\n\n"
        try:
            agent_result = await run_agent_pipeline(business_id, trigger="new_data")
            n_alerts = agent_result.get("alerts_generated", 0)
            n_wa = agent_result.get("whatsapp_sent", 0)
            yield f"data: {json.dumps({'type': 'step', 'step': 'agents', 'status': 'done', 'message': f'Analysis complete: {n_alerts} alerts generated, {n_wa} WhatsApp sent'})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'step', 'step': 'agents', 'status': 'error', 'message': f'Agent pipeline error: {str(e)}'})}\n\n"

        # Final summary
        summary = {
            "type": "complete",
            "upload_id": upload_id,
            "rows_total": final_result.get("rows_total", 0),
            "rows_cleaned": final_result.get("rows_cleaned", 0),
            "rows_flagged": final_result.get("rows_flagged", 0),
            "cleaned_csv_url": f"/api/upload/download/{upload_id}",
        }
        yield f"data: {json.dumps(summary)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/download/{upload_id}")
async def download_cleaned_csv(upload_id: str):
    """Download the cleaned CSV produced by the pipeline."""
    csv_bytes = _cleaned_csv_store.get(upload_id)
    if not csv_bytes:
        raise HTTPException(404, "Upload not found or expired")
    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=cleaned_{upload_id}.csv"},
    )
