from fastapi import APIRouter, Query
from typing import Optional
from app.seed_data import get_store

router = APIRouter(prefix="/internal/v1/requisitions", tags=["Requisitions Mock API"])


@router.get("")
def list_requisitions(
    status: Optional[str] = Query(None),
    job_family: Optional[str] = Query(None),
    level: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    org: Optional[str] = Query(None),
    team: Optional[str] = Query(None),
    hiring_manager_id: Optional[str] = Query(None),
    recruiter_id: Optional[str] = Query(None),
    days_open_gt: Optional[int] = Query(None, description="Filter reqs open longer than N days"),
    limit: int = Query(100, le=500),
    offset: int = Query(0),
):
    data = get_store().get("requisitions", [])
    if status:
        data = [r for r in data if r["status"].lower() == status.lower()]
    if job_family:
        data = [r for r in data if r["job_family"].lower() == job_family.lower()]
    if level:
        data = [r for r in data if r["level"].lower() == level.lower()]
    if location:
        data = [r for r in data if r["location"].lower() == location.lower()]
    if org:
        data = [r for r in data if r["org"].lower() == org.lower()]
    if team:
        data = [r for r in data if r["team"].lower() == team.lower()]
    if hiring_manager_id:
        data = [r for r in data if r["hiring_manager_id"] == hiring_manager_id]
    if recruiter_id:
        data = [r for r in data if r["recruiter_id"] == recruiter_id]
    if days_open_gt is not None:
        data = [r for r in data if r["days_open"] > days_open_gt]
    total = len(data)
    return {"total": total, "offset": offset, "limit": limit, "data": data[offset: offset + limit]}


@router.get("/{req_id}")
def get_requisition(req_id: str):
    data = get_store().get("requisitions", [])
    for r in data:
        if r["req_id"] == req_id:
            return r
    return {"error": f"Requisition {req_id} not found"}


@router.get("/summary/by-org")
def summary_by_org():
    data = get_store().get("requisitions", [])
    summary: dict = {}
    for r in data:
        org = r["org"]
        if org not in summary:
            summary[org] = {"Open": 0, "Closed": 0, "On Hold": 0, "total_headcount": 0}
        summary[org][r["status"]] = summary[org].get(r["status"], 0) + 1
        summary[org]["total_headcount"] += r["headcount"]
    return {"data": summary}


@router.get("/summary/at-risk")
def at_risk_reqs(days_threshold: int = Query(60)):
    data = get_store().get("requisitions", [])
    import datetime
    today = datetime.date.today()
    at_risk = []
    for r in data:
        if r["status"] == "Open":
            target = datetime.date.fromisoformat(r["target_start_date"])
            days_to_target = (target - today).days
            if days_to_target < 30 and r["days_open"] > days_threshold:
                r = dict(r, days_to_target=days_to_target, risk_level="High" if days_to_target < 14 else "Medium")
                at_risk.append(r)
    return {"total": len(at_risk), "data": at_risk}
