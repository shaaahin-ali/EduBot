"""
Objection handler — empathetic, practical responses when students
raise cost, time, or doubt objections.
"""

from groq import Groq
from config import GROQ_API_KEY, LLM_MODEL

client = Groq(api_key=GROQ_API_KEY)

_SYSTEM = """\
You are a warm, empathetic admissions counsellor at a coaching academy.

The student has raised an objection (cost, time, doubt, or unsure).

Your reply must do exactly three things:
1. Validate their concern in ONE sentence — show you heard them.
2. Offer ONE concrete fact or alternative (see context below).
3. End with ONE question that gives them agency over the next step.

Tone: human, calm, confident — not pushy or salesy.
Length: 5–7 lines maximum. Use 1–2 emojis at most.

Pricing context you may reference:
- JEE Advanced Crash Course: Rs 28,000 / 6 months (~Rs 155/day)
- NEET Full Package (PCB):   Rs 42,000 / year   (~Rs 115/day)
- Python & Data Science:     Rs 15,000 / 4 months
- EMI available: Rs 5,000/month (no interest)
- Scholarship: 20% off for 85%+ marks
- Free demo class before any commitment
- 30-day money-back guarantee — no questions asked
"""

_FALLBACK = (
    "I completely understand — it's a big decision and cost matters. 💭\n\n"
    "A few things that might help:\n"
    "• *Free demo class* before you commit to anything\n"
    "• *EMI option* — Rs 5,000/month, no extra charges\n"
    "• *Scholarship* — 20% off if your marks are 85%+\n\n"
    "Would any of these work for you?"
)


def handle_objection(user_message: str, student_name: str | None = None) -> str:
    """Generate an empathetic objection response via Groq."""
    name_ctx = f"Student's name: {student_name}.\n" if student_name else ""
    prompt   = f"{name_ctx}Student message: {user_message}"
    try:
        response = client.chat.completions.create(
            model=LLM_MODEL,
            max_tokens=220,
            temperature=0.65,
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user",   "content": prompt},
            ],
        )
        return response.choices[0].message.content.strip()
    except Exception as exc:
        print(f"[objection_handler] Error: {exc}")
        return _FALLBACK
