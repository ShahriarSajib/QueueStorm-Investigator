"""
QueueStorm Investigator — main FastAPI application.

Endpoints:
  GET  /health          → {"status": "ok"}
  POST /analyze-ticket  → TicketResponse
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from .engine import run_engine
from . import history
from .llm import generate_texts
from .models import (
    HistoryEntryResponse,
    HistoryListResponse,
    HistoryStatsResponse,
    TicketRequest,
    TicketResponse,
)
from .safety import validate_customer_reply, validate_next_action

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="QueueStorm Investigator",
    description="AI/API SupportOps copilot for digital finance complaints",
    version="1.0.0",
)


# ---------------------------------------------------------------------------
# Exception handlers — never expose stack traces or secrets
# ---------------------------------------------------------------------------

@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    return JSONResponse(
        status_code=422,
        content={"error": "Semantic validation failed", "detail": exc.errors()},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error. Please try again later."},
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/analyze-ticket", response_model=TicketResponse)
async def analyze_ticket(ticket: TicketRequest):
    try:
        # Step 1: Rule engine — all structured fields
        engine_result = run_engine(ticket)

        # Step 2: LLM — three natural-language fields
        texts = await generate_texts(ticket, engine_result)

        # Step 3: Safety validation — post-process text fields
        safe_reply = validate_customer_reply(texts["customer_reply"], ticket.language)
        safe_action = validate_next_action(texts["recommended_next_action"])

        response = TicketResponse(
            ticket_id=ticket.ticket_id,
            relevant_transaction_id=engine_result.relevant_transaction_id,
            evidence_verdict=engine_result.evidence_verdict,
            case_type=engine_result.case_type,
            severity=engine_result.severity,
            department=engine_result.department,
            agent_summary=texts["agent_summary"],
            recommended_next_action=safe_action,
            customer_reply=safe_reply,
            human_review_required=engine_result.human_review_required,
            confidence=engine_result.confidence,
            reason_codes=engine_result.reason_codes,
        )

        # Record to history
        history.append(ticket, response)

        return response

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("analyze_ticket error: %s", exc)
        raise HTTPException(status_code=500, detail="Internal error processing ticket")


# ---------------------------------------------------------------------------
# History endpoints
# ---------------------------------------------------------------------------


@app.get("/history", response_model=HistoryListResponse)
async def list_history(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    case_type: str | None = Query(None),
    severity: str | None = Query(None),
    department: str | None = Query(None),
    verdict: str | None = Query(None),
):
    entries = history.list_entries(
        limit=limit,
        offset=offset,
        case_type=case_type,
        severity=severity,
        department=department,
        verdict=verdict,
    )
    return HistoryListResponse(
        total=history.count(case_type=case_type, severity=severity),
        entries=[HistoryEntryResponse(**e) for e in entries],
    )


@app.get("/history/stats", response_model=HistoryStatsResponse)
async def history_stats():
    return history.stats()


@app.get("/history/{ticket_id}", response_model=HistoryEntryResponse)
async def get_history_entry(ticket_id: str):
    entry = history.get_entry(ticket_id)
    if not entry:
        raise HTTPException(status_code=404, detail="History entry not found")
    return HistoryEntryResponse(**entry)


@app.delete("/history/{ticket_id}")
async def delete_history_entry(ticket_id: str):
    deleted = history.delete_entry(ticket_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="History entry not found")
    return {"status": "deleted", "ticket_id": ticket_id}