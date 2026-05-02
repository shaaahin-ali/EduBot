"""
EduBot — FastAPI application.
Routes:
    POST /inbound   → Twilio WhatsApp webhook
    GET  /leads     → Admin endpoint to view captured leads
    GET  /health    → Health check
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Form, Depends, Query, Request
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session as DBSession

from database import get_db, init_db
from models import Lead
from session_manager import (
    get_session, IDLE, AWAITING_CHOICE, is_in_enrollment,
    update_context, dominant_sentiment, set_state
)
from intent_classifier import classify
from rag_engine import init_rag, answer as rag_answer
from lead_manager import start_enrollment, handle_enrollment_step
from objection_handler import handle_objection
from analytics import compute_metrics
from audio_handler import transcribe_audio

# Optional scheduler
try:
    from scheduler import start_scheduler, schedule_followup
    SCHEDULER_AVAILABLE = True
except ImportError:
    SCHEDULER_AVAILABLE = False


# ── Lifespan ─────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[main] Initializing database…")
    init_db()
    print("[main] Initializing RAG engine…")
    init_rag()
    if SCHEDULER_AVAILABLE:
        start_scheduler()
    print("[main] EduBot is ready!")
    yield
    print("[main] Shutting down…")


app = FastAPI(title="EduBot", version="1.0.0", lifespan=lifespan)

# Serve brochure images publicly via /static/images/
app.mount("/static", StaticFiles(directory="static"), name="static")


# ── Static replies ───────────────────────────────────────────
GREETING_REPLY = (
    "Hi! 👋 I'm *EduBot*, your personal admissions assistant at EduBot Academy.\n\n"
    "I'm here to help with:\n"
    "✨ Finding the perfect course for YOUR goals\n"
    "💬 Answering ANY questions about fees, schedules, etc.\n"
    "📝 Helping you enroll in a free demo class\n\n"
    "Before we start, what brings you here today?\n"
    "A) Looking for a specific course (JEE? Python?)\n"
    "B) Just exploring what we offer\n"
    "C) Ready to enroll!\n\n"
    "_(Or just type your question — I'll figure it out!)_"
)

ESCALATION_REPLY = (
    "It sounds like this needs a bit more dedicated attention than I can provide right now. 🤝\n\n"
    "Let me connect you with our Head Counsellor, Priya. "
    "I'm sending her our chat history so you don't have to repeat yourself.\n\n"
    "She'll message you back right here within an hour. In the meantime, feel free to browse our website!"
)

OTHER_REPLY = (
    "I'm not sure I understood that. 🤔\n\n"
    "Try asking about our *courses*, *fees*, or *schedules* — "
    "or say *enroll* to sign up!"
)


# ── Brochure picker ──────────────────────────────────────────
def _pick_brochure(base_url: str, message: str) -> str | None:
    """
    Return a publicly accessible image URL for the relevant brochure,
    or None if no clear match.
    """
    msg = message.lower()
    if any(k in msg for k in ["jee", "iit", "advanced", "foundation"]):
        return f"{base_url}static/images/jee_brochure.png"
    elif any(k in msg for k in ["neet", "mbbs", "biology", "pcb", "medical"]):
        return f"{base_url}static/images/neet_brochure.png"
    else:
        # For general course / fee / schedule queries → show all courses
        return f"{base_url}static/images/general_brochure.png"


# ── TwiML builder ────────────────────────────────────────────
def _build_twiml(body: str, media_url: str | None = None) -> str:
    """Wrap a reply in TwiML, optionally attaching a media image."""
    safe = (
        body
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    media_tag = f"\n        <Media>{media_url}</Media>" if media_url else ""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f"<Response><Message>{safe}{media_tag}</Message></Response>"
    )


# ── Core routing ─────────────────────────────────────────────
def _route_message(
    wa_number: str,
    text: str,
    db: DBSession,
    base_url: str,
) -> tuple[str, str | None]:
    
    session = get_session(wa_number)

    # 1. Active enrollment slot-filling
    if is_in_enrollment(wa_number):
        return handle_enrollment_step(wa_number, text, db), None

    # 2. Classify intent + sentiment
    classification = classify(text)
    intent    = classification["intent"]
    sentiment = classification["sentiment"]
    print(f"[main] {wa_number} | intent={intent} | sentiment={sentiment} | msg={text[:40]}")

    # 3. Update rich context memory
    update_context(wa_number, intent, sentiment, text)
    
    # Check auto-escalation trigger
    if session.get("escalate"):
        session["escalate"] = False  # Reset so we don't spam it
        return ESCALATION_REPLY, None

    # 4. Handle Greeting / Awaiting Choice
    if intent == "GREETING":
        set_state(wa_number, AWAITING_CHOICE)
        return GREETING_REPLY, None
        
    if session["state"] == AWAITING_CHOICE:
        set_state(wa_number, IDLE)
        msg_lower = text.lower().strip()
        if msg_lower == "a":
            return "Great! What course are you looking for? We have JEE, NEET, Python, and Spoken English.", None
        elif msg_lower == "b":
            return "Awesome. We specialize in engineering/medical test prep and tech skills. Any particular area you're curious about?", None
        elif msg_lower == "c":
            return start_enrollment(wa_number, text), None

    # 5. Handle Objection
    if intent == "OBJECTION":
        name = session.get("name")
        return handle_objection(text, name), None

    # 6. Handle Enrollment
    if intent == "ENROL":
        return start_enrollment(wa_number, text), None

    # 7. Handle RAG Queries (Course/Fee/Schedule/Eligibility)
    if intent in ("COURSE_INFO", "FEE_QUERY", "SCHEDULE", "ELIGIBILITY"):
        # Increment FOMO counter
        session["course_query_count"] += 1
        
        reply = rag_answer(text, session, sentiment)
        
        # Inject FOMO discount message exactly on the 3rd inquiry
        if session["course_query_count"] == 3 and not session["fomo_triggered"]:
            session["fomo_triggered"] = True
            reply += (
                "\n\n🎁 *SPECIAL OFFER UNLOCKED* 🎁\n"
                "I notice you're really interested in this! I just spoke to my manager, "
                "and if you enroll in the next 2 hours, I can give you a *10% discount* on your fees.\n\n"
                "Say *enroll* right now to claim it! ⏳"
            )
            
        return reply, None

    # 8. Fallback
    return "I didn't quite catch that. Try asking about our courses, fees, or say 'enroll' to sign up! 🤔", None


# ── Routes ───────────────────────────────────────────────────
@app.post("/inbound", response_class=PlainTextResponse)
async def inbound(
    request: Request,
    Body: str = Form(default=""),
    From: str = Form(...),
    To: str = Form(default=""),
    NumMedia: int = Form(default=0),
    db: DBSession = Depends(get_db),
):
    """Twilio WhatsApp webhook — receives messages (text or audio), returns TwiML."""
    text_to_process = Body

    # ── Voice Note Handling ──
    if NumMedia > 0:
        form_data = await request.form()
        media_url = form_data.get("MediaUrl0")
        content_type = form_data.get("MediaContentType0", "")
        
        if media_url and "audio" in content_type:
            print(f"[main] Voice note received from {From}, transcribing...")
            transcribed_text = transcribe_audio(media_url)
            if transcribed_text:
                text_to_process = transcribed_text
                print(f"[main] Transcribed text: {text_to_process}")

    if not text_to_process.strip():
        # Fallback if transcription failed and no text was sent
        reply = "Sorry, I couldn't understand that voice note. Could you try typing it? 🎙️"
        return PlainTextResponse(
            content=_build_twiml(reply, None),
            media_type="application/xml",
        )

    # Build base URL dynamically from the incoming request
    base_url = str(request.base_url)

    reply, media_url = _route_message(
        wa_number=From, text=text_to_process, db=db, base_url=base_url
    )
    return PlainTextResponse(
        content=_build_twiml(reply, media_url),
        media_type="application/xml",
    )


@app.get("/leads")
def get_leads(
    status: str = Query(default=None, description="Filter: new, contacted, enrolled"),
    db: DBSession = Depends(get_db),
):
    """Admin endpoint — returns rich funnel metrics + captured leads."""
    metrics = compute_metrics(db)
    
    query = db.query(Lead)
    if status:
        query = query.filter(Lead.status == status)
    leads = query.order_by(Lead.created_at.desc()).all()
    
    return {
        "analytics": metrics,
        "leads_count": len(leads),
        "leads": [l.to_dict() for l in leads]
    }


@app.get("/health")
def health():
    return {"status": "ok", "service": "EduBot"}
