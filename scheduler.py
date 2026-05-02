"""
Optional APScheduler module — sends a WhatsApp follow-up 24h after lead capture.
"""

from datetime import datetime, timedelta, timezone
from apscheduler.schedulers.background import BackgroundScheduler
from twilio.rest import Client
from config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_NUMBER

_scheduler = None


def _send_followup(wa_number: str, name: str) -> None:
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        client.messages.create(
            from_=TWILIO_WHATSAPP_NUMBER, to=wa_number,
            body=f"Hi {name}! 👋 Just checking in — did you have any questions about the course? Reply anytime!",
        )
        print(f"[scheduler] Follow-up sent to {wa_number}")
    except Exception as e:
        print(f"[scheduler] Failed: {e}")


def start_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        return
    _scheduler = BackgroundScheduler()
    _scheduler.start()
    print("[scheduler] APScheduler started")


def schedule_followup(lead_id: int, wa_number: str, name: str) -> None:
    if _scheduler is None:
        print("[scheduler] Scheduler not started — skipping")
        return
    run_at = datetime.now(timezone.utc) + timedelta(hours=24)
    _scheduler.add_job(
        _send_followup, "date", run_date=run_at,
        args=[wa_number, name], id=f"followup_{lead_id}", replace_existing=True,
    )
    print(f"[scheduler] Follow-up for lead {lead_id} scheduled at {run_at.isoformat()}")
