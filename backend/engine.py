"""
Rule-based investigator engine.
Produces all structured fields deterministically — no LLM involved.
LLM only generates the three natural-language text fields afterwards.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from .models import TicketRequest, TransactionEntry


# ---------------------------------------------------------------------------
# Keyword lists
# ---------------------------------------------------------------------------

PHISHING_KEYWORDS = [
    "otp", "one time password", "pin", "password", "পিন", "ওটিপি",
    "calling from bkash", "calling from bKash", "bkash employee", "bKash employee",
    "verify account", "account will be blocked", "blocked account",
    "verify your account", "suspend", "suspended", "আপনার একাউন্ট",
    "ব্লক হয়ে যাবে", "ব্লক করা হবে",
]

TRANSFER_KEYWORDS = [
    "wrong number", "wrong person", "wrong account", "sent to wrong",
    "ভুল নম্বর", "ভুল পাঠিয়েছি", "ভুল একাউন্ট",
    "sent to a wrong", "sent by mistake",
]

PAYMENT_FAILED_KEYWORDS = [
    "failed", "balance deducted", "balance was deducted", "money deducted",
    "টাকা কেটে", "কাটা হয়েছে", "failed but", "shows failed",
]

REFUND_KEYWORDS = [
    "refund", "return my money", "return the money", "get my money back",
    "রিফান্ড", "টাকা ফেরত",
]

DUPLICATE_KEYWORDS = [
    "deducted twice", "charged twice", "paid twice", "double charge",
    "double payment", "two times", "duplicate",
]

MERCHANT_SETTLE_KEYWORDS = [
    "settlement", "not settled", "settlement delay", "settle", "pending settlement",
    "সেটেলমেন্ট", "সেটেল",
]

AGENT_CASHIN_KEYWORDS = [
    "cash in", "cash-in", "cashin", "agent", "ক্যাশ ইন", "ক্যাশইন",
    "এজেন্ট",
]

DUPLICATE_WINDOW_SECONDS = 120  # two identical payments within this window → duplicate


# ---------------------------------------------------------------------------
# Internal result dataclass
# ---------------------------------------------------------------------------

@dataclass
class EngineResult:
    relevant_transaction_id: Optional[str] = None
    evidence_verdict: str = "insufficient_data"
    case_type: str = "other"
    severity: str = "low"
    department: str = "customer_support"
    human_review_required: bool = False
    confidence: float = 0.5
    reason_codes: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _contains_any(text: str, keywords: list[str]) -> bool:
    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in keywords)


def _extract_amounts(text: str) -> list[float]:
    """Pull numeric amounts mentioned in the complaint."""
    raw = re.findall(r"\b(\d[\d,]*(?:\.\d+)?)\b", text)
    amounts = []
    for r in raw:
        try:
            amounts.append(float(r.replace(",", "")))
        except ValueError:
            pass
    return amounts


def _mentions_today_or_yesterday(text: str) -> tuple[bool, bool]:
    """Return (mentions_today, mentions_yesterday)."""
    low = text.lower()
    today = any(w in low for w in ["today", "আজ", "আজকে"])
    yesterday = any(w in low for w in ["yesterday", "গতকাল"])
    return today, yesterday


def _parse_ts(ts: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return None


def _score_transaction(txn: TransactionEntry, complaint: str, amounts: list[float]) -> float:
    """Score how well a transaction matches the complaint (0–4)."""
    score = 0.0
    low = complaint.lower()

    # Amount match
    for amt in amounts:
        if abs(txn.amount - amt) < 1:
            score += 2.0
            break
        elif abs(txn.amount - amt) / max(txn.amount, 1) < 0.15:
            score += 1.0
            break

    # Time match
    ts = _parse_ts(txn.timestamp)
    if ts:
        now = datetime.now(tz=timezone.utc)
        age_days = (now - ts).days
        today, yesterday = _mentions_today_or_yesterday(complaint)
        if today and age_days == 0:
            score += 1.0
        elif yesterday and age_days == 1:
            score += 1.0
        elif age_days <= 1:
            score += 0.3

    # Type match
    type_keywords = {
        "transfer": ["sent", "transfer", "পাঠিয়েছি", "পাঠানো"],
        "payment": ["paid", "pay", "payment", "recharge", "bill", "পেমেন্ট"],
        "cash_in": ["cash in", "cashin", "ক্যাশ ইন"],
        "cash_out": ["cash out", "withdraw"],
        "settlement": ["settlement", "settle"],
        "refund": ["refund"],
    }
    for kw in type_keywords.get(txn.type, []):
        if kw in low:
            score += 0.5
            break

    return score


def _detect_duplicate(txns: list[TransactionEntry]) -> Optional[str]:
    """Return transaction_id of suspected duplicate (second identical payment)."""
    payments = [t for t in txns if t.type == "payment" and t.status == "completed"]
    for i in range(len(payments)):
        for j in range(i + 1, len(payments)):
            a, b = payments[i], payments[j]
            if abs(a.amount - b.amount) < 0.01 and a.counterparty == b.counterparty:
                ts_a = _parse_ts(a.timestamp)
                ts_b = _parse_ts(b.timestamp)
                if ts_a and ts_b and abs((ts_b - ts_a).total_seconds()) <= DUPLICATE_WINDOW_SECONDS:
                    # Return the later one as the suspected duplicate
                    return b.transaction_id if ts_b >= ts_a else a.transaction_id
    return None


def _count_prior_transfers_to(txns: list[TransactionEntry], counterparty: str, exclude_id: str) -> int:
    return sum(
        1 for t in txns
        if t.counterparty == counterparty and t.transaction_id != exclude_id and t.type == "transfer"
    )


# ---------------------------------------------------------------------------
# Main engine function
# ---------------------------------------------------------------------------

def run_engine(ticket: TicketRequest) -> EngineResult:
    result = EngineResult()
    complaint = ticket.complaint
    history = ticket.transaction_history or []
    amounts = _extract_amounts(complaint)

    # ------------------------------------------------------------------
    # Step 1: Phishing detection — highest priority, overrides everything
    # ------------------------------------------------------------------
    if _contains_any(complaint, PHISHING_KEYWORDS):
        result.case_type = "phishing_or_social_engineering"
        result.severity = "critical"
        result.department = "fraud_risk"
        result.relevant_transaction_id = None
        result.evidence_verdict = "insufficient_data"
        result.human_review_required = True
        result.confidence = 0.95
        result.reason_codes = ["phishing", "credential_protection", "critical_escalation"]
        return result

    # ------------------------------------------------------------------
    # Step 2: Duplicate payment detection
    # ------------------------------------------------------------------
    if _contains_any(complaint, DUPLICATE_KEYWORDS) or _detect_duplicate(history):
        dup_id = _detect_duplicate(history)
        if dup_id:
            result.relevant_transaction_id = dup_id
            result.evidence_verdict = "consistent"
            result.confidence = 0.93
        else:
            result.relevant_transaction_id = None
            result.evidence_verdict = "insufficient_data"
            result.confidence = 0.6
        result.case_type = "duplicate_payment"
        result.severity = "high"
        result.department = "payments_ops"
        result.human_review_required = True
        result.reason_codes = ["duplicate_payment", "biller_verification_required"]
        return result

    # ------------------------------------------------------------------
    # Step 3: Transaction matching (score each transaction)
    # ------------------------------------------------------------------
    best_txn: Optional[TransactionEntry] = None
    best_score = 0.0
    second_score = 0.0

    for txn in history:
        score = _score_transaction(txn, complaint, amounts)
        if score > best_score:
            second_score = best_score
            best_score = score
            best_txn = txn
        elif score > second_score:
            second_score = score

    # If scores are too close, treat as ambiguous
    if best_txn and best_score > 0 and (best_score - second_score) < 0.5 and second_score > 0:
        result.relevant_transaction_id = None
        result.evidence_verdict = "insufficient_data"
        result.case_type = "wrong_transfer"  # most common in ambiguous multi-txn
        result.severity = "medium"
        result.department = "dispute_resolution"
        result.human_review_required = False
        result.confidence = 0.65
        result.reason_codes = ["ambiguous_match", "needs_clarification"]
        return result

    if best_txn and best_score >= 1.0:
        result.relevant_transaction_id = best_txn.transaction_id
    else:
        result.relevant_transaction_id = None

    # ------------------------------------------------------------------
    # Step 4: Case type detection from complaint keywords + txn data
    # ------------------------------------------------------------------

    # Agent cash-in
    if _contains_any(complaint, AGENT_CASHIN_KEYWORDS) and (
        ticket.user_type == "agent"
        or any(t.type == "cash_in" for t in history)
        or (best_txn and best_txn.type == "cash_in")
    ):
        result.case_type = "agent_cash_in_issue"
        result.severity = "high"
        result.department = "agent_operations"
        result.human_review_required = True
        result.reason_codes = ["agent_cash_in", "pending_transaction", "agent_ops"]
        if best_txn:
            result.evidence_verdict = "consistent"
            result.confidence = 0.88
        else:
            result.evidence_verdict = "insufficient_data"
            result.confidence = 0.6

    # Merchant settlement delay
    elif _contains_any(complaint, MERCHANT_SETTLE_KEYWORDS) or ticket.user_type == "merchant":
        result.case_type = "merchant_settlement_delay"
        result.severity = "medium"
        result.department = "merchant_operations"
        result.human_review_required = False
        result.reason_codes = ["merchant_settlement", "delay", "pending"]
        if best_txn:
            result.evidence_verdict = "consistent"
            result.confidence = 0.92
        else:
            result.evidence_verdict = "insufficient_data"
            result.confidence = 0.6

    # Wrong transfer
    elif _contains_any(complaint, TRANSFER_KEYWORDS) or (best_txn and best_txn.type == "transfer"):
        result.case_type = "wrong_transfer"
        result.department = "dispute_resolution"
        result.human_review_required = True
        result.reason_codes = ["wrong_transfer", "transaction_match", "dispute_initiated"]

        if best_txn:
            prior_count = _count_prior_transfers_to(history, best_txn.counterparty, best_txn.transaction_id)
            if prior_count >= 2:
                # Established recipient — inconsistent
                result.evidence_verdict = "inconsistent"
                result.severity = "medium"
                result.confidence = 0.75
                result.reason_codes = ["wrong_transfer_claim", "established_recipient_pattern", "evidence_inconsistent"]
            else:
                result.evidence_verdict = "consistent"
                result.severity = "high"
                result.confidence = 0.9
        else:
            result.evidence_verdict = "insufficient_data"
            result.severity = "medium"
            result.confidence = 0.6

    # Payment failed
    elif _contains_any(complaint, PAYMENT_FAILED_KEYWORDS) or (best_txn and best_txn.status == "failed"):
        result.case_type = "payment_failed"
        result.severity = "high"
        result.department = "payments_ops"
        result.human_review_required = False
        result.reason_codes = ["payment_failed", "potential_balance_deduction"]
        if best_txn:
            result.evidence_verdict = "consistent"
            result.confidence = 0.9
        else:
            result.evidence_verdict = "insufficient_data"
            result.confidence = 0.6

    # Refund request
    elif _contains_any(complaint, REFUND_KEYWORDS):
        result.case_type = "refund_request"
        result.severity = "low"
        result.department = "customer_support"
        result.human_review_required = False
        result.reason_codes = ["refund_request", "merchant_policy_dependent"]
        if best_txn:
            result.evidence_verdict = "consistent"
            result.confidence = 0.85
        else:
            result.evidence_verdict = "insufficient_data"
            result.confidence = 0.6

    # Fallback: vague / other
    else:
        result.case_type = "other"
        result.severity = "low"
        result.department = "customer_support"
        result.human_review_required = False
        result.relevant_transaction_id = None
        result.evidence_verdict = "insufficient_data"
        result.confidence = 0.5
        result.reason_codes = ["vague_complaint", "needs_clarification"]

    # ------------------------------------------------------------------
    # Step 5: Override human_review_required for high/critical severity
    # ------------------------------------------------------------------
    if result.severity in ("high", "critical"):
        result.human_review_required = True
    if result.evidence_verdict == "inconsistent":
        result.human_review_required = True

    return result