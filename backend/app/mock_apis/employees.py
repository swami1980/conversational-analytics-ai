from fastapi import APIRouter, Query
from typing import Optional
from app.seed_data import get_store

router = APIRouter(prefix="/internal/v1/employees", tags=["Employees Mock API"])


@router.get("")
def list_employees(
    status: Optional[str] = Query(None),
    org: Optional[str] = Query(None),
    team: Optional[str] = Query(None),
    job_family: Optional[str] = Query(None),
    level: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    manager_id: Optional[str] = Query(None),
    tenure_lt: Optional[float] = Query(None, description="Tenure less than N years"),
    tenure_gt: Optional[float] = Query(None, description="Tenure greater than N years"),
    limit: int = Query(100, le=500),
    offset: int = Query(0),
):
    data = get_store().get("employees", [])
    if status:
        data = [e for e in data if e["status"].lower() == status.lower()]
    if org:
        data = [e for e in data if e["org"].lower() == org.lower()]
    if team:
        data = [e for e in data if e["team"].lower() == team.lower()]
    if job_family:
        data = [e for e in data if e["job_family"].lower() == job_family.lower()]
    if level:
        data = [e for e in data if e["level"].lower() == level.lower()]
    if location:
        data = [e for e in data if e["location"].lower() == location.lower()]
    if manager_id:
        data = [e for e in data if e["manager_id"] == manager_id]
    if tenure_lt is not None:
        data = [e for e in data if e["tenure_years"] < tenure_lt]
    if tenure_gt is not None:
        data = [e for e in data if e["tenure_years"] > tenure_gt]
    total = len(data)
    return {"total": total, "offset": offset, "limit": limit, "data": data[offset: offset + limit]}


@router.get("/headcount/by-org")
def headcount_by_org():
    data = get_store().get("employees", [])
    active = [e for e in data if e["status"] == "Active"]
    result: dict = {}
    for e in active:
        org = e["org"]
        if org not in result:
            result[org] = {"total": 0, "by_job_family": {}, "by_level": {}, "by_location": {}}
        result[org]["total"] += 1
        jf = e["job_family"]
        result[org]["by_job_family"][jf] = result[org]["by_job_family"].get(jf, 0) + 1
        lvl = e["level"]
        result[org]["by_level"][lvl] = result[org]["by_level"].get(lvl, 0) + 1
        loc = e["location"]
        result[org]["by_location"][loc] = result[org]["by_location"].get(loc, 0) + 1
    return {"total_active": len(active), "by_org": result}


@router.get("/attrition/summary")
def attrition_summary():
    data = get_store().get("employees", [])
    departed = [e for e in data if e["status"] == "Departed"]
    total = len(data)
    by_org: dict = {}
    by_reason: dict = {}
    for e in departed:
        org = e["org"]
        by_org[org] = by_org.get(org, 0) + 1
        reason = e.get("departure_reason", "Unknown")
        by_reason[reason] = by_reason.get(reason, 0) + 1
    return {
        "total_employees": total,
        "total_departed": len(departed),
        "overall_attrition_rate": round(len(departed) / total, 3) if total else 0,
        "by_org": by_org,
        "by_reason": by_reason,
    }


@router.get("/{employee_id}")
def get_employee(employee_id: str):
    data = get_store().get("employees", [])
    for e in data:
        if e["employee_id"] == employee_id:
            return e
    return {"error": f"Employee {employee_id} not found"}
