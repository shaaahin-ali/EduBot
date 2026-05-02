"""
Lead capture state machine v2 — conversational slot-filling.

Follows a natural flow rather than robotic form filling.
Saves the completed lead to SQLite.
"""

from __future__ import annotations
from sqlalchemy.orm import Session as DBSession

from models import Lead
from session_manager import (
    get_session, reset_session, set_state, set_slot,
    IDLE, ASK_NAME, ASK_PHONE, ASK_COURSE, ASK_TIME, AWAITING_CHOICE
)


def start_enrollment(wa_number: str, message: str) -> str:
    """Kick off the conversational enrollment flow."""
    session = get_session(wa_number)
    
    # Try to extract a name if they said "I am Rahul and I want to enroll"
    # For now, we'll just ask gracefully.
    
    # Use context if we have it
    course_context = f" for {session['interests'][-1]}" if session['interests'] else ""
    
    set_state(wa_number, ASK_NAME)
    return (
        f"Awesome! Let's get you set up{course_context}. 🎉\n\n"
        "Just a few quick details so our counsellor can confirm your demo slot.\n\n"
        "What should I call you? 😊"
    )


def handle_enrollment_step(wa_number: str, user_message: str, db: DBSession) -> str:
    """Process current enrollment step, fill slot, advance state."""
    session = get_session(wa_number)
    state = session["state"]
    text = user_message.strip()

    if state == ASK_NAME:
        set_slot(wa_number, "name", text)
        set_state(wa_number, ASK_PHONE)
        return (
            f"Perfect, {text}! 👋\n\n"
            "And what's the best WhatsApp number to send the demo link to?"
        )

    elif state == ASK_PHONE:
        set_slot(wa_number, "phone", text)
        set_state(wa_number, ASK_COURSE)
        
        # If we already know their interest, skip asking or confirm it
        if session["interests"]:
            inferred_course = session["interests"][-1]
            set_slot(wa_number, "course_interest", inferred_course)
            set_state(wa_number, ASK_TIME)
            return (
                f"Got it! 📝 I see you're interested in *{inferred_course}*.\n\n"
                "One last thing — when would you prefer the demo?\n"
                "⏰ This Saturday (morning/evening)\n"
                "⏰ This Sunday (morning/evening)\n"
                "⏰ Weekday evening (which day?)"
            )
        else:
            return (
                "Got it! 📝\n\n"
                "Which course are you most interested in?\n"
                "_(e.g. JEE, NEET, Python Bootcamp, Spoken English)_"
            )

    elif state == ASK_COURSE:
        set_slot(wa_number, "course_interest", text)
        set_state(wa_number, ASK_TIME)
        return (
            "Almost done! ⏰\n\n"
            "When would you prefer the demo?\n"
            "⏰ This Saturday (morning/evening)\n"
            "⏰ This Sunday (morning/evening)\n"
            "⏰ Weekday evening (which day?)"
        )

    elif state == ASK_TIME:
        set_slot(wa_number, "preferred_time", text)
        
        # Save lead to DB
        slots = session["slots"]
        name = slots["name"]
        
        try:
            lead = Lead(
                wa_number=wa_number,
                name=name,
                phone=slots["phone"],
                course_interest=slots["course_interest"],
                preferred_time=slots["preferred_time"],
                status="new",
            )
            db.add(lead)
            db.commit()
        except Exception as e:
            print(f"[lead_manager] DB save error: {e}")
            db.rollback()

        # Reset session but keep memory
        reset_session(wa_number)
        
        # Restore name to context memory
        set_slot(wa_number, "name", name)

        return (
            f"✅ All set, {name}!\n\n"
            "Here's what happens next:\n"
            "📱 Our counsellor will confirm your slot within 2 hours.\n"
            f"🎥 We'll send the Zoom link to {slots['phone']}.\n\n"
            "Any other questions before then? I'm here 24/7! 🚀"
        )

    return "Hmm, let's start over. Type *enroll* to begin again."

