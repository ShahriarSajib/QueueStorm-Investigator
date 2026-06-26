"""
History tracker — persists analysis results to a JSON-lines file.

Provides:
  - append()   record a new analysis
  - list()     paginated list with optional filters
  - get()      retrieve a single entry by ticket_id
  - delete()   remove an entry by ticket_id
  - stats()    aggregate statistics over stored entries
"""

from __future__ import annotations

import json
import logging
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .models import TicketRequest, TicketResponse

logger = logging.getLogger(__name__)

HISTORY_DIR = Path(os.getenv("HISTORY_DIR", "./data"))
HISTORY_FILE = HISTORY_DIR / "history.jsonl"
_LOCK = threading.Lock()


class HistoryEntry:
    """A single stored analysis record."""

    def __init__(
        self,
        ticket_id: str,
        request: TicketRequest,
        response: TicketResponse,
        analyzed_at: Optional[str] = None,
    ) -> None:
        self.ticket_id = ticket_id
        self.request = request
        self.response = response
        self.analyzed_at = analyzed_at or datetime.now(tz=timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return {
            "ticket_id": self.ticket_id,
            "request": self.request.model_dump(),
            "response": self.response.model_dump(),
            "analyzed_at": self.analyzed_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> HistoryEntry:
        return cls(
            ticket_id=data["ticket_id"],
            request=TicketRequest(**data["request"]),
            response=TicketResponse(**data["response"]),
            analyzed_at=data.get("analyzed_at"),
        )


# ---------------------------------------------------------------------------
# File helpers
# ---------------------------------------------------------------------------


def _ensure_dir() -> None:
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)


def _read_all() -> list[dict]:
    """Read every line from the history file. Returns list of dicts."""
    _ensure_dir()
    if not HISTORY_FILE.exists():
        return []
    entries: list[dict] = []
    with _LOCK:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        logger.warning("Skipping malformed history line")
    return entries


def _write_all(entries: list[dict]) -> None:
    """Overwrite the history file with the given entries (one JSON object per line)."""
    _ensure_dir()
    with _LOCK:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            for entry in entries:
                f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def append(request: TicketRequest, response: TicketResponse) -> None:
    """Append a new analysis result to the history file."""
    entry = HistoryEntry(
        ticket_id=response.ticket_id,
        request=request,
        response=response,
    )
    _ensure_dir()
    with _LOCK:
        with open(HISTORY_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry.to_dict(), ensure_ascii=False, default=str) + "\n")
    logger.info("History recorded for ticket %s", response.ticket_id)


def list_entries(
    limit: int = 20,
    offset: int = 0,
    case_type: Optional[str] = None,
    severity: Optional[str] = None,
    department: Optional[str] = None,
    verdict: Optional[str] = None,
) -> list[dict]:
    """Return a filtered, paginated list of history entries (newest first)."""
    entries = _read_all()
    # Reverse so newest is first
    entries.reverse()

    if case_type:
        entries = [e for e in entries if e.get("response", {}).get("case_type") == case_type]
    if severity:
        entries = [e for e in entries if e.get("response", {}).get("severity") == severity]
    if department:
        entries = [e for e in entries if e.get("response", {}).get("department") == department]
    if verdict:
        entries = [e for e in entries if e.get("response", {}).get("evidence_verdict") == verdict]

    return entries[offset : offset + limit]


def get_entry(ticket_id: str) -> Optional[dict]:
    """Retrieve a single history entry by ticket_id."""
    for entry in _read_all():
        if entry.get("ticket_id") == ticket_id:
            return entry
    return None


def delete_entry(ticket_id: str) -> bool:
    """Delete a history entry by ticket_id. Returns True if deleted."""
    entries = _read_all()
    new_entries = [e for e in entries if e.get("ticket_id") != ticket_id]
    if len(new_entries) == len(entries):
        return False
    _write_all(new_entries)
    logger.info("Deleted history entry for ticket %s", ticket_id)
    return True


def count(case_type: Optional[str] = None, severity: Optional[str] = None) -> int:
    """Count entries, optionally filtered."""
    entries = _read_all()
    if case_type:
        entries = [e for e in entries if e.get("response", {}).get("case_type") == case_type]
    if severity:
        entries = [e for e in entries if e.get("response", {}).get("severity") == severity]
    return len(entries)


def stats() -> dict:
    """Return aggregate statistics over all history entries."""
    entries = _read_all()
    total = len(entries)
    if total == 0:
        return {"total": 0, "by_case_type": {}, "by_severity": {}, "by_department": {}, "by_verdict": {}}

    case_types: dict[str, int] = {}
    severities: dict[str, int] = {}
    departments: dict[str, int] = {}
    verdicts: dict[str, int] = {}

    for e in entries:
        resp = e.get("response", {})
        key = resp.get("case_type", "unknown")
        case_types[key] = case_types.get(key, 0) + 1
        key = resp.get("severity", "unknown")
        severities[key] = severities.get(key, 0) + 1
        key = resp.get("department", "unknown")
        departments[key] = departments.get(key, 0) + 1
        key = resp.get("evidence_verdict", "unknown")
        verdicts[key] = verdicts.get(key, 0) + 1

    return {
        "total": total,
        "by_case_type": case_types,
        "by_severity": severities,
        "by_department": departments,
        "by_verdict": verdicts,
    }
