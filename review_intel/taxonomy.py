"""Journeys follow the core user journeys of an Indian broking app; issues are a fixed set so counts compare across apps."""
import re

APPS = {"com.msf.angelmobile": "Angel One", "com.zerodha.kite3": "Zerodha Kite",
        "com.nextbillion.groww": "Groww", "in.upstox.app": "Upstox"}

JOURNEYS = {
    "onboarding_kyc": "Account opening & KYC",
    "funds": "Adding / withdrawing funds",
    "orders_trading": "Orders & day-to-day trading",
    "discovery_research": "Discovery & research",
    "portfolio_tracking": "Portfolio tracking",
    "charges_pricing": "Charges & pricing",
    "support_service": "Customer support",
    "account_access": "Login & account access",
    "app_performance": "App stability & speed",
    "general": "General / no specific journey",
}
ISSUES = {
    "delay": "Delay / waiting", "failure": "Failure or error", "confusing_ux": "Confusing UX",
    "missing_feature": "Missing feature", "crash_slow": "Crash or slowness", "unexpected_charges": "Unexpected charges",
    "poor_support": "Poor support", "praise": "Praise", "other": "Other",
}

# keyword baseline (also the fallback when the LLM is unavailable). Order matters: first match wins.
_J = [
    ("onboarding_kyc", r"\bkyc\b|account open|open(ing)? (an |my )?account|verification|verify|document|aadhaa?r|\bpan\b|e-?sign|video kyc|activation|activate|onboard"),
    ("funds", r"withdraw|add(ing)? (money|funds?)|deposit|payout|\bupi\b|not credited|refund|fund transfer|payment (failed|pending)|money (stuck|deducted)"),
    ("charges_pricing", r"brokerage|charges?\b|hidden (fee|cost)|\bamc\b|\bdp charge|fees?\b|expensive|deduct"),
    ("account_access", r"log ?in|otp|password|\bmpin\b|logged out|log ?out|blocked|2fa|biometric|pin\b"),
    ("support_service", r"customer (care|support|service)|support team|no response|ticket|helpline|call back|executive|chat ?bot"),
    ("orders_trading", r"\border|f&o|option|future|intraday|chart|watchlist|stop ?loss|\bgtt\b|execution|position|square ?off|trade\b|trading"),
    ("portfolio_tracking", r"portfolio|holding|p&?l\b|profit and loss|statement|returns? (not|wrong)|mutual fund"),
    ("discovery_research", r"recommend|research|advis|screener|tips?\b|ideas?\b|\barq\b|analysis|news"),
    ("app_performance", r"crash|slow|lag|hang|bug|not (working|opening|loading)|stuck|freez|glitch|update"),
]
_I = [
    ("unexpected_charges", r"hidden|extra charge|deduct|overcharg|brokerage|\bamc\b"),
    ("poor_support", r"no response|customer (care|support)|ticket|no one|nobody|not (helpful|responding)"),
    ("crash_slow", r"crash|slow|lag|hang|freez|not (opening|loading)"),
    ("delay", r"delay|pending|waiting|days|hours|still not|long time|taking time"),
    ("failure", r"fail|error|rejected|not working|unable|can'?t|cannot|not credited|stuck|wrong"),
    ("confusing_ux", r"confus|difficult|complicated|hard to|not clear|interface|ui\b|design"),
    ("missing_feature", r"please add|need (a|an)? ?feature|missing|no option|should (add|have)|wish"),
    ("praise", r"good|great|best|excellent|awesome|nice|easy|love|smooth|helpful"),
]


def keyword_label(text: str):
    t = (text or "").lower()
    journey = next((j for j, p in _J if re.search(p, t)), "general")
    issue = next((i for i, p in _I if re.search(p, t)), "other")
    return journey, issue


def sentiment_from_score(score) -> str:
    s = int(score)
    return "negative" if s <= 2 else ("neutral" if s == 3 else "positive")
