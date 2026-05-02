"""
Configuration — loads all secrets and settings from environment variables.
Create a .env file in the project root with:
    GROQ_API_KEY=gsk_...
    GEMINI_API_KEY=AIza...    (optional backup)
    TWILIO_ACCOUNT_SID=AC...
    TWILIO_AUTH_TOKEN=...
    TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
    DATABASE_URL=sqlite:///./edubot.db
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── Groq (primary LLM) ──────────────────────────────────────
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
LLM_MODEL: str = "llama-3.1-8b-instant"

# ── Gemini (backup LLM — optional) ──────────────────────────
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

# ── Twilio ───────────────────────────────────────────────────
TWILIO_ACCOUNT_SID: str = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_WHATSAPP_NUMBER: str = os.getenv(
    "TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886"
)

# ── Database ─────────────────────────────────────────────────
DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./edubot.db")
