"""
Analytics — lead funnel metrics for the /leads admin endpoint.
"""

from __future__ import annotations
from collections import Counter
from sqlalchemy.orm import Session as DBSession
from models import Lead


def compute_metrics(db: DBSession) -> dict:
    """
    Returns a funnel summary derived from the leads table.
    Designed to be shown in the demo to prove business impact.
    """
    all_leads = db.query(Lead).all()
    total     = len(all_leads)

    if total == 0:
        return {
            "total_leads": 0,
            "by_status": {},
            "top_courses": {},
            "conversion_rate_pct": 0.0,
            "note": "No leads captured yet.",
        }

    status_counts = Counter(l.status          for l in all_leads)
    course_counts = Counter(l.course_interest for l in all_leads)
    enrolled      = status_counts.get("enrolled", 0)

    return {
        "total_leads":           total,
        "by_status":             dict(status_counts),
        "top_courses":           dict(course_counts.most_common(5)),
        "conversion_rate_pct":   round((enrolled / total) * 100, 1),
    }
