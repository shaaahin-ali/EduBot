"""
Intent + sentiment classifier — single Groq call, returns both labels.

Intents (8):  GREETING | COURSE_INFO | ELIGIBILITY | FEE_QUERY |
              SCHEDULE | ENROL | OBJECTION | OTHER
Sentiments (4): excited | frustrated | confused | neutral
"""

from __future__ import annotations
import json
from groq import Groq
from config import GROQ_API_KEY, LLM_MODEL

client = Groq(api_key=GROQ_API_KEY)

VALID_INTENTS = {
    "GREETING", "COURSE_INFO", "ELIGIBILITY",
    "FEE_QUERY", "SCHEDULE", "ENROL", "OBJECTION", "OTHER",
}
VALID_SENTIMENTS = {"excited", "frustrated", "confused", "neutral"}

_SYSTEM = """\
You are an intent and sentiment classifier for a coaching academy chatbot.

Return ONLY a JSON object with two keys — no markdown, no explanation:
  "intent":    GREETING | COURSE_INFO | ELIGIBILITY | FEE_QUERY | SCHEDULE | ENROL | OBJECTION | OTHER
  "sentiment": excited | frustrated | confused | neutral

Intent guide:
  GREETING    — hi, hello, hey, good morning
  COURSE_INFO — what courses, tell me about, syllabus
  ELIGIBILITY — can I join if, do I need, requirements
  FEE_QUERY   — fee, price, cost, payment, scholarship, discount
  SCHEDULE    — timing, days, batch, hours, when are classes
  ENROL       — enroll, register, book demo, sign up, join
  OBJECTION   — too expensive, can't afford, no time, not sure it's for me
  OTHER       — anything else

Sentiment guide:
  excited    — enthusiasm, "!", "omg", positive words
  frustrated — complaints, "don't think", giving up, "too hard"
  confused   — "not sure", "which one", "help me decide"
  neutral    — plain factual question

Example output: {"intent": "FEE_QUERY", "sentiment": "neutral"}
"""


def classify(user_message: str) -> dict[str, str]:
    """
    Classify intent and sentiment in a single LLM call.
    Returns {"intent": str, "sentiment": str}.
    Falls back to {"intent": "OTHER", "sentiment": "neutral"} on any error.
    """
    try:
        response = client.chat.completions.create(
            model=LLM_MODEL,
            max_tokens=40,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user",   "content": user_message},
            ],
        )
        data      = json.loads(response.choices[0].message.content)
        intent    = str(data.get("intent",    "OTHER")).upper()
        sentiment = str(data.get("sentiment", "neutral")).lower()
        return {
            "intent":    intent    if intent    in VALID_INTENTS    else "OTHER",
            "sentiment": sentiment if sentiment in VALID_SENTIMENTS else "neutral",
        }
    except Exception as exc:
        print(f"[classifier] Error: {exc}")
        return {"intent": "OTHER", "sentiment": "neutral"}
