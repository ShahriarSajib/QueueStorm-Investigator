from pydantic import BaseModel, Field, field_validator
from typing import Literal, Optional


class TransactionEntry(BaseModel):
    transaction_id: str
    timestamp: str
    type: Literal["transfer", "payment", "cash_in", "cash_out", "settlement", "refund"]
    amount: float
    counterparty: str
    status: Literal["completed", "failed", "pending", "reversed"]


class TicketRequest(BaseModel):
    ticket_id: str
    complaint: str
    language: Optional[Literal["en", "bn", "mixed"]] = None
    channel: Optional[Literal["in_app_chat", "call_center", "email", "merchant_portal", "field_agent"]] = None
    user_type: Optional[Literal["customer", "merchant", "agent", "unknown"]] = None
    campaign_context: Optional[str] = None
    transaction_history: list[TransactionEntry] = Field(default_factory=list)
    metadata: Optional[dict] = None

    @field_validator("complaint")
    @classmethod
    def complaint_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("complaint cannot be empty")
        return v


class TicketResponse(BaseModel):
    ticket_id: str
    relevant_transaction_id: Optional[str]
    evidence_verdict: Literal["consistent", "inconsistent", "insufficient_data"]
    case_type: Literal[
        "wrong_transfer",
        "payment_failed",
        "refund_request",
        "duplicate_payment",
        "merchant_settlement_delay",
        "agent_cash_in_issue",
        "phishing_or_social_engineering",
        "other",
    ]
    severity: Literal["low", "medium", "high", "critical"]
    department: Literal[
        "customer_support",
        "dispute_resolution",
        "payments_ops",
        "merchant_operations",
        "agent_operations",
        "fraud_risk",
    ]
    agent_summary: str
    recommended_next_action: str
    customer_reply: str
    human_review_required: bool
    confidence: Optional[float] = None
    reason_codes: Optional[list[str]] = None


class HistoryEntryResponse(BaseModel):
    ticket_id: str
    request: TicketRequest
    response: TicketResponse
    analyzed_at: str


class HistoryListResponse(BaseModel):
    total: int
    entries: list[HistoryEntryResponse]


class HistoryStatsResponse(BaseModel):
    total: int
    by_case_type: dict[str, int]
    by_severity: dict[str, int]
    by_department: dict[str, int]
    by_verdict: dict[str, int]