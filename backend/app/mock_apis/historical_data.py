from fastapi import APIRouter, Query
from typing import Optional
from app.seed_data import get_store

router = APIRouter(prefix="/internal/v1/historical-data", tags=["Historical Data Mock API"])

PERIOD_ORDER = ["Q1 2024", "Q2 2024", "Q3 2024", "Q4 2024", "Q1 2025", "Q2 2025", "Q3 2025", "Q4 2025"]


@router.get("")
def list_historical(
    period: Optional[str] = Query(None),
    org: Optional[str] = Query(None),
    limit: int = Query(200, le=1000),
    offset: int = Query(0),
):
    data = get_store().get("historical_data", [])
    if period:
        data = [h for h in data if h["period"].lower() == period.lower()]
    if org:
        data = [h for h in data if h["org"].lower() == org.lower()]
    data.sort(key=lambda h: (PERIOD_ORDER.index(h["period"]) if h["period"] in PERIOD_ORDER else 99, h["org"]))
    total = len(data)
    return {"total": total, "offset": offset, "limit": limit, "data": data[offset: offset + limit]}


@router.get("/headcount-trend")
def headcount_trend(org: Optional[str] = Query(None)):
    data = get_store().get("historical_data", [])
    if org:
        data = [h for h in data if h["org"].lower() == org.lower()]
    by_period: dict = {}
    for h in data:
        p = h["period"]
        if p not in by_period:
            by_period[p] = {"headcount_end": 0, "new_hires": 0, "attrition": 0}
        by_period[p]["headcount_end"] += h["headcount_end"]
        by_period[p]["new_hires"] += h["new_hires"]
        by_period[p]["attrition"] += h["attrition_count"]
    result = [{"period": p, **by_period[p]} for p in PERIOD_ORDER if p in by_period]
    return {"org": org or "all", "data": result}


@router.get("/hiring-velocity")
def hiring_velocity(org: Optional[str] = Query(None)):
    data = get_store().get("historical_data", [])
    if org:
        data = [h for h in data if h["org"].lower() == org.lower()]
    by_period: dict = {}
    for h in data:
        p = h["period"]
        if p not in by_period:
            by_period[p] = {"total_hires": 0, "plan": 0, "attainment_sum": 0, "count": 0}
        by_period[p]["total_hires"] += h["new_hires"]
        by_period[p]["plan"] += h["hiring_plan"]
        by_period[p]["attainment_sum"] += h["plan_attainment"]
        by_period[p]["count"] += 1
    result = []
    for p in PERIOD_ORDER:
        if p in by_period:
            v = by_period[p]
            result.append({
                "period": p,
                "total_hires": v["total_hires"],
                "hiring_plan": v["plan"],
                "plan_attainment": round(v["total_hires"] / max(1, v["plan"]), 3),
            })
    return {"org": org or "all", "data": result}


@router.get("/attrition-trend")
def attrition_trend(org: Optional[str] = Query(None)):
    data = get_store().get("historical_data", [])
    if org:
        data = [h for h in data if h["org"].lower() == org.lower()]
    by_period: dict = {}
    for h in data:
        p = h["period"]
        if p not in by_period:
            by_period[p] = {"attrition": 0, "headcount": 0}
        by_period[p]["attrition"] += h["attrition_count"]
        by_period[p]["headcount"] += h["headcount_start"]
    result = []
    for p in PERIOD_ORDER:
        if p in by_period:
            v = by_period[p]
            result.append({
                "period": p,
                "attrition_count": v["attrition"],
                "headcount": v["headcount"],
                "attrition_rate": round(v["attrition"] / max(1, v["headcount"]), 3),
            })
    return {"org": org or "all", "data": result}
