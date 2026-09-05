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
    language: str | None = Form(None),
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

        # If language is passed, ensure profile is updated
        if language:
            try:
                prof = await db.get_business_profile(business_id) or {}
                prof["language"] = language
                await db.upsert_business_profile(prof)
            except Exception:
                pass

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

        # ── INSTANT INGESTION RECEIPT — WhatsApp ────────────────────────────
        try:
            prof = await db.get_business_profile(business_id) or {}
            phone = prof.get("mobile") or prof.get("phone") or prof.get("whatsapp_number") or "9518948695"
            biz_name = prof.get("business_name", "Your Enterprise")
            rows_ingested = len(final_result.get("transactions", []))
            rows_cleaned = final_result.get("rows_cleaned", rows_ingested)
            rows_flagged = final_result.get("rows_flagged", 0)
            if phone:
                from services.twilio_service import send_whatsapp_alert
                receipt_msg = (
                    f"✅ *Bizpanion — Data Ingested*\n\n"
                    f"*{biz_name}* — your CSV has been processed.\n\n"
                    f"📊 Rows ingested: *{rows_ingested}*\n"
                    f"🧹 Cleaned: *{rows_cleaned}* | Flagged: *{rows_flagged}*\n\n"
                    f"🤖 Running autonomous analysis — alerts will follow shortly.\n\n"
                    f"_Open Bizpanion app to view real-time insights._"
                )
                try:
                    send_whatsapp_alert(phone, receipt_msg)
                    yield f"data: {json.dumps({'type': 'step', 'step': 'whatsapp', 'status': 'done', 'message': f'Ingestion receipt sent to WhatsApp {phone[-4:]}'})}\n\n"
                except Exception as wa_e:
                    yield f"data: {json.dumps({'type': 'step', 'step': 'whatsapp', 'status': 'warn', 'message': f'WhatsApp receipt skipped: {str(wa_e)[:60]}'})}\n\n"
        except Exception as prof_e:
            logger.warning(f"WhatsApp receipt: {prof_e}")

        # Trigger agent pipeline
        yield f"data: {json.dumps({'type': 'step', 'step': 'agents', 'status': 'running', 'message': 'Running autonomous analysis agents...'})}\n\n"
        try:
            agent_result = await run_agent_pipeline(business_id, trigger="new_data")
            n_alerts = agent_result.get("alerts_generated", 0)
            n_wa = agent_result.get("whatsapp_sent", 0)
            yield f"data: {json.dumps({'type': 'step', 'step': 'agents', 'status': 'done', 'message': f'Analysis complete: {n_alerts} alerts generated in selected regional dialect, {n_wa} WhatsApp sent'})}\n\n"
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


from pydantic import BaseModel

class LoadSampleRequest(BaseModel):
    business_id: str
    sector: str = "kirana"
    language: str | None = None


@router.post("/load-sample")
async def load_sample_dataset(req: LoadSampleRequest):
    """
    1-Click instant loader for demo datasets:
    Supports: kirana, dairy, textile, hardware, vegetables
    Ingests CSV, updates profile business_type, updates inventory, and triggers agent pipeline.
    """
    from pathlib import Path
    sector_map = {
        "kirana": "kirana_grocery_sales.csv",
        "grocery": "kirana_grocery_sales.csv",
        "dairy": "dairy_farm_sales.csv",
        "textile": "textile_garments_sales.csv",
        "hardware": "hardware_electrical_sales.csv",
        "vegetables": "vegetable_vendor_sales.csv",
        "produce": "vegetable_vendor_sales.csv",
    }
    
    filename = sector_map.get(req.sector.lower(), "kirana_grocery_sales.csv")
    base_dir = Path(__file__).resolve().parent.parent
    csv_path = base_dir / "sample_data" / filename
    
    if not csv_path.exists():
        csv_path = Path("sample_data") / filename
        if not csv_path.exists():
            raise HTTPException(404, f"Sample file {filename} not found at {csv_path}")
        
    with open(csv_path, "rb") as f:
        file_bytes = f.read()

    # Process through pipeline
    gen = run_pipeline(file_bytes, req.business_id, DataSource.CSV)
    final_result = {}
    try:
        while True:
            next(gen)
    except StopIteration as e:
        final_result = e.value or {}

    transactions = final_result.get("transactions", [])
    written = 0
    if transactions:
        written = await db.insert_transactions(transactions)

    # Cache cleaned CSV so it is instantly downloadable
    upload_id = str(uuid.uuid4())
    csv_bytes = generate_cleaned_csv(transactions)
    _cleaned_csv_store[upload_id] = csv_bytes

    # Update business profile business_type & language if provided
    profile = await db.get_business_profile(req.business_id) or {}
    updated_profile = {
        **profile,
        "id": req.business_id,
        "business_type": req.sector.lower(),
        "whatsapp_number": profile.get("whatsapp_number") or profile.get("mobile") or profile.get("phone") or "9518948695",
    }
    if req.language:
        updated_profile["language"] = req.language
    await db.upsert_business_profile(updated_profile)

    # Trigger agent pipeline
    agent_res = {}
    try:
        agent_res = await run_agent_pipeline(req.business_id, trigger="sample_data")
    except Exception as e:
        logger.warning(f"Agent pipeline triggered with error: {e}")

    # ── AUTO WhatsApp Ingestion Notification ─────────────────────────────────
    try:
        phone = updated_profile["whatsapp_number"]
        biz_name = updated_profile.get("business_name") or "Gourav Clothing Store"
        if phone:
            from services.twilio_service import send_whatsapp_alert
            wa_msg = (
                f"📥 *Bizpanion — {req.sector.title()} Data Ingested Autonomously*\n\n"
                f"*{biz_name}* — sector demo data ingested successfully.\n\n"
                f"📊 {written} records · {final_result.get('rows_cleaned', written)} cleaned\n"
                f"🤖 {agent_res.get('alerts_generated', 0)} alerts generated\n"
                f"📱 {agent_res.get('whatsapp_sent', 0)} alerts dispatched to WhatsApp\n\n"
                f"_View your dashboard for live market benchmarks & insights._"
            )
            try:
                wa_sid = send_whatsapp_alert(phone, wa_msg)
                logger.info(f"Auto WhatsApp sent for sample load: {req.sector} to {phone}, SID={wa_sid}")
            except Exception as wa_e:
                logger.warning(f"Auto WhatsApp failed: {wa_e}")
    except Exception as e:
        logger.warning(f"Auto WhatsApp setup failed: {e}")

    return {
        "status": "success",
        "sector": req.sector,
        "filename": filename,
        "upload_id": upload_id,
        "cleaned_csv_url": f"/api/upload/download/{upload_id}",
        "records_ingested": written,
        "rows_total": final_result.get("rows_total", len(transactions)),
        "rows_cleaned": final_result.get("rows_cleaned", len(transactions)),
        "rows_flagged": final_result.get("rows_flagged", 0),
        "alerts_generated": agent_res.get("alerts_generated", 0),
        "whatsapp_dispatched": agent_res.get("whatsapp_sent", 0),
        "message": f"Successfully loaded {written} {req.sector} records into active ledger!",
    }

