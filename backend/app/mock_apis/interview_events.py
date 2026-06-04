from fastapi import APIRouter, Query
from typing import Optional
from app.seed_data import get_store

router = APIRouter(prefix="/internal/v1/interview-events", tags=["Interview Events Mock API"])


@router.get("")
def list_interview_events(
    candidate_id: Optional[str] = Query(None),
    req_id: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None),
    outcome: Optional[str] = Query(None),
    org: Optional[str] = Query(None),
    job_family: Optional[str] = Query(None),
    interviewer_id: Optional[str] = Query(None),
    scheduled_after: Optional[str] = Query(None, description="ISO date"),
    scheduled_before: Optional[str] = Query(None, description="ISO date"),
    is_bar_raiser_session: Optional[bool] = Query(None),
    feedback_submitted: Optional[bool] = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0),
):
    data = get_store().get("interview_events", [])
    if candidate_id:
        data = [e for e in data if e["candidate_id"] == candidate_id]
    if req_id:
        data = [e for e in data if e["req_id"] == req_id]
    if event_type:
        data = [e for e in data if e["event_type"].lower() == event_type.lower()]
    if outcome:
        data = [e for e in data if e["outcome"].lower() == outcome.lower()]
    if org:
        data = [e for e in data if e["org"].lower() == org.lower()]
    if job_family:
        data = [e for e in data if e["job_family"].lower() == job_family.lower()]
    if interviewer_id:
        data = [e for e in data if e["interviewer_id"] == interviewer_id]
    if scheduled_after:
        data = [e for e in data if e["scheduled_date"] >= scheduled_after]
    if scheduled_before:
        data = [e for e in data if e["scheduled_date"] <= scheduled_before]
    if is_bar_raiser_session is not None:
        data = [e for e in data if e["is_bar_raiser_session"] == is_bar_raiser_session]
    if feedback_submitted is not None:
        data = [e for e in data if e["feedback_submitted"] == feedback_submitted]
    data.sort(key=lambda e: e["scheduled_date"])
    total = len(data)
    return {"total": total, "offset": offset, "limit": limit, "data": data[offset: offset + limit]}


@router.get("/bar-raiser/schedule")
def bar_raiser_schedule(scheduled_after: Optional[str] = Query(None), scheduled_before: Optional[str] = Query(None)):
    import datetime
    today = datetime.date.today()
    after = scheduled_after or today.isoformat()
    before = scheduled_before or (today + datetime.timedelta(days=14)).isoformat()
    data = get_store().get("interview_events", [])
    sessions = [
        e for e in data
        if e["is_bar_raiser_session"] and e["outcome"] == "Pending"
        and e["scheduled_date"] >= after and e["scheduled_date"] <= before
    ]
    sessions.sort(key=lambda e: e["scheduled_date"])
    return {"total": len(sessions), "date_range": {"from": after, "to": before}, "data": sessions}


@router.get("/feedback/missing")
def missing_feedback():
    data = get_store().get("interview_events", [])
    import datetime
    today = datetime.date.today()
    missing = [
        e for e in data
        if e["scheduled_date"] <= today.isoformat() and not e["feedback_submitted"] and e["outcome"] != "Pending"
    ]
    return {"total": len(missing), "data": missing}


@router.get("/{event_id}")
def get_event(event_id: str):
    data = get_store().get("interview_events", [])
    for e in data:
        if e["event_id"] == event_id:
            return e
    return {"error": f"Event {event_id} not found"}
