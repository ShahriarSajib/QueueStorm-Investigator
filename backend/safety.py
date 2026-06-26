"""
Safety validator.
Runs on every response before it is returned.
Replaces any customer_reply or recommended_next_action that contains
a safety violation with a hardcoded safe fallback.
"""

SAFE_FALLBACK_EN = (
    "We have received your request and our support team will review it shortly. "
    "Please do not share your PIN or OTP with anyone, including anyone claiming to be from our team."
)

SAFE_FALLBACK_BN = (
    "আমরা আপনার অনুরোধ পেয়েছি এবং আমাদের সাপোর্ট টিম শীঘ্রই পর্যালোচনা করবে। "
    "অনুগ্রহ করে কারো সাথে আপনার পিন বা ওটিপি শেয়ার করবেন না।"
)

# Phrases that must NEVER appear in customer_reply
BANNED_CUSTOMER_REPLY_PHRASES = [
    "your pin", "your otp", "your password", "share your pin",
    "share your otp", "enter your pin", "verify your otp",
    "type your pin", "provide your pin", "provide your otp",
    "আপনার পিন", "আপনার ওটিপি", "পিন দিন", "ওটিপি দিন",
]

# Phrases that must NEVER appear in customer_reply OR recommended_next_action
# (unauthorized refund/reversal/unblock confirmation)
BANNED_REFUND_PHRASES = [
    "we will refund", "we will reverse", "your account will be unblocked",
    "you will receive a refund", "refund will be processed",
    "your money will be returned", "we'll refund", "we'll reverse",
    "আমরা রিফান্ড করব", "টাকা ফেরত দেওয়া হবে",
]

# Third-party redirect phrases
BANNED_THIRD_PARTY_PHRASES = [
    "contact a third party", "call this number", "whatsapp us at",
    "telegram", "unofficial",
]


def _contains_banned(text: str, phrases: list[str]) -> bool:
    low = text.lower()
    return any(p.lower() in low for p in phrases)


def validate_customer_reply(reply: str, language: str | None = "en") -> str:
    """Return a safe customer reply, replacing with fallback if any violation found."""
    if _contains_banned(reply, BANNED_CUSTOMER_REPLY_PHRASES):
        return SAFE_FALLBACK_BN if language == "bn" else SAFE_FALLBACK_EN
    if _contains_banned(reply, BANNED_REFUND_PHRASES):
        return SAFE_FALLBACK_BN if language == "bn" else SAFE_FALLBACK_EN
    if _contains_banned(reply, BANNED_THIRD_PARTY_PHRASES):
        return SAFE_FALLBACK_BN if language == "bn" else SAFE_FALLBACK_EN
    return reply


def validate_next_action(action: str) -> str:
    """Sanitize recommended_next_action — remove unauthorized refund confirmations."""
    if _contains_banned(action, BANNED_REFUND_PHRASES):
        return (
            "Route this case to the appropriate operations team for investigation "
            "and resolution per standard policy."
        )
    return action