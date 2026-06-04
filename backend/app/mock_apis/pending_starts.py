from fastapi import APIRouter, Query
from typing import Optional
import datetime
from app.seed_data import get_store

router = APIRouter(prefix="/internal/v1/pending-starts", tags=["Pending Starts Mock API"])


@router.get("")
def list_pending_starts(
    status: Optional[str] = Query(None),
    org: Optional[str] = Query(None),
    job_family: Optional[str] = Query(None),
    level: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    hiring_manager_id: Optional[str] = Query(None),
    start_before: Optional[str] = Query(None, description="ISO date — filter starts before this date"),
    start_after: Optional[str] = Query(None, description="ISO date — filter starts after this date"),
    laptop_provisioned: Optional[bool] = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0),
):
    data = get_store().get("pending_starts", [])
    if status:
        data = [s for s in data if s["status"].lower() == status.lower()]
    if org:
        data = [s for s in data if s["org"].lower() == org.lower()]
    if job_family:
        data = [s for s in data if s["job_family"].lower() == job_family.lower()]
    if level:
        data = [s for s in data if s["level"].lower() == level.lower()]
    if location:
        data = [s for s in data if s["location"].lower() == location.lower()]
    if hiring_manager_id:
        data = [s for s in data if s["hiring_manager_id"] == hiring_manager_id]
    if start_before:
        data = [s for s in data if s["start_date"] <= start_before]
    if start_after:
        data = [s for s in data if s["start_date"] >= start_after]
    if laptop_provisioned is not None:
        data = [s for s in data if s["laptop_provisioned"] == laptop_provisioned]
    data.sort(key=lambda s: s["start_date"])
    total = len(data)
    return {"total": total, "offset": offset, "limit": limit, "data": data[offset: offset + limit]}


@router.get("/onboarding/readiness")
def onboarding_readiness():
    data = get_store().get("pending_starts", [])
    today = datetime.date.today()
    thirty_days = (today + datetime.timedelta(days=30)).isoformat()
    upcoming = [s for s in data if s["start_date"] <= thirty_days and s["status"] != "Deferred"]
    at_risk = [s for s in upcoming if not s["laptop_provisioned"] or not s["badge_requested"]]
    return {
        "starting_within_30_days": len(upcoming),
        "fully_provisioned": len(upcoming) - len(at_risk),
        "at_risk_onboarding": len(at_risk),
        "at_risk_details": at_risk,
    }


@router.get("/{pending_start_id}")
def get_pending_start(pending_start_id: str):
    data = get_store().get("pending_starts", [])
    for s in data:
        if s["pending_start_id"] == pending_start_id:
            return s
    return {"error": f"Pending start {pending_start_id} not found"}
