"""
Session manager — rich per-user conversation state.

Each session tracks state, enrollment slots, context memory
(name, interests, sentiment history) and escalation signals.
"""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Any

# ── State constants ───────────────────────────────────────────
IDLE             = "IDLE"
AWAITING_CHOICE  = "AWAITING_CHOICE"   # after greeting A/B/C prompt
ASK_NAME         = "ASK_NAME"
ASK_PHONE        = "ASK_PHONE"
ASK_COURSE       = "ASK_COURSE"
ASK_TIME         = "ASK_TIME"

_ENROLLMENT_STATES = {ASK_NAME, ASK_PHONE, ASK_COURSE, ASK_TIME}

# ── In-memory store ───────────────────────────────────────────
_sessions: dict[str, dict[str, Any]] = {}


def _fresh() -> dict[str, Any]:
    return {
        "state": IDLE,
        "slots": {"name": None, "phone": None, "course_interest": None, "preferred_time": None},
        # context memory
        "name": None,               # mirrors slots["name"] once filled
        "interests": [],            # course topics they've mentioned
        "sentiment_history": [],    # last 5 sentiment labels
        "objection_count": 0,
        "question_count": 0,
        "course_query_count": 0,    # Tracks how many times they asked about a course
        "fomo_triggered": False,    # Ensures we only offer the discount once
        "escalate": False,
        "started_at": datetime.now(timezone.utc).isoformat(),
    }


def get_session(wa_number: str) -> dict[str, Any]:
    if wa_number not in _sessions:
        _sessions[wa_number] = _fresh()
    return _sessions[wa_number]


def reset_session(wa_number: str) -> None:
    _sessions[wa_number] = _fresh()


def set_state(wa_number: str, state: str) -> None:
    get_session(wa_number)["state"] = state


def set_slot(wa_number: str, key: str, value: str) -> None:
    session = get_session(wa_number)
    session["slots"][key] = value
    if key == "name":
        session["name"] = value   # quick-access shortcut


def is_in_enrollment(wa_number: str) -> bool:
    return get_session(wa_number)["state"] in _ENROLLMENT_STATES


def update_context(wa_number: str, intent: str, sentiment: str, message: str) -> None:
    """Called after every message to keep session context fresh."""
    session = get_session(wa_number)
    session["question_count"] += 1

    # Track last 5 sentiments
    session["sentiment_history"].append(sentiment)
    if len(session["sentiment_history"]) > 5:
        session["sentiment_history"].pop(0)

    # Extract interest keywords
    msg = message.lower()
    for kw, label in [
        ("jee", "JEE"), ("iit", "JEE"),
        ("neet", "NEET"), ("mbbs", "NEET"), ("biology", "NEET"),
        ("python", "Python"), ("data science", "Python"), ("coding", "Python"),
        ("english", "English"), ("spoken", "English"),
    ]:
        if kw in msg and label not in session["interests"]:
            session["interests"].append(label)

    if intent == "OBJECTION":
        session["objection_count"] += 1

    # Auto-escalate: frustrated 2+ times or 3+ objections
    frustrated = session["sentiment_history"].count("frustrated")
    if frustrated >= 2 or session["objection_count"] >= 3:
        session["escalate"] = True


def dominant_sentiment(wa_number: str) -> str:
    history = get_session(wa_number)["sentiment_history"]
    if not history:
        return "neutral"
    return max(set(history), key=history.count)
