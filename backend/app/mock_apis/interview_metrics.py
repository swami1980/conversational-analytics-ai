from fastapi import APIRouter, Query
from typing import Optional
from app.seed_data import get_store

router = APIRouter(prefix="/internal/v1/interview-metrics", tags=["Interview Metrics Mock API"])


@router.get("")
def list_metrics(
    period: Optional[str] = Query(None, description="e.g. 'Q1 2025'"),
    org: Optional[str] = Query(None),
    job_family: Optional[str] = Query(None),
    limit: int = Query(200, le=1000),
    offset: int = Query(0),
):
    data = get_store().get("interview_metrics", [])
    if period:
        data = [m for m in data if m["period"].lower() == period.lower()]
    if org:
        data = [m for m in data if m["org"].lower() == org.lower()]
    if job_family:
        data = [m for m in data if m["job_family"].lower() == job_family.lower()]
    total = len(data)
    return {"total": total, "offset": offset, "limit": limit, "data": data[offset: offset + limit]}


@router.get("/time-to-hire/by-job-family")
def time_to_hire_by_job_family(period: Optional[str] = Query(None), org: Optional[str] = Query(None)):
    data = get_store().get("interview_metrics", [])
    if period:
        data = [m for m in data if m["period"].lower() == period.lower()]
    if org:
        data = [m for m in data if m["org"].lower() == org.lower()]
    by_jf: dict = {}
    for m in data:
        jf = m["job_family"]
        if jf not in by_jf:
            by_jf[jf] = {"total_days": 0, "count": 0}
        by_jf[jf]["total_days"] += m["avg_time_to_hire_days"]
        by_jf[jf]["count"] += 1
    result = {
        jf: {"avg_time_to_hire_days": round(v["total_days"] / v["count"], 1), "sample_size": v["count"]}
        for jf, v in by_jf.items()
    }
    return {"period": period or "all", "org": org or "all", "data": result}


@router.get("/offer-acceptance/trend")
def offer_acceptance_trend(org: Optional[str] = Query(None), job_family: Optional[str] = Query(None)):
    data = get_store().get("interview_metrics", [])
    if org:
        data = [m for m in data if m["org"].lower() == org.lower()]
    if job_family:
        data = [m for m in data if m["job_family"].lower() == job_family.lower()]
    by_period: dict = {}
    for m in data:
        p = m["period"]
        if p not in by_period:
            by_period[p] = {"total_rate": 0, "count": 0, "total_offers": 0, "total_hires": 0}
        by_period[p]["total_rate"] += m["offer_acceptance_rate"]
        by_period[p]["count"] += 1
        by_period[p]["total_offers"] += m["total_offers"]
        by_period[p]["total_hires"] += m["total_hires"]
    PERIOD_ORDER = ["Q1 2024", "Q2 2024", "Q3 2024", "Q4 2024", "Q1 2025", "Q2 2025", "Q3 2025", "Q4 2025"]
    result = []
    for p in PERIOD_ORDER:
        if p in by_period:
            v = by_period[p]
            result.append({
                "period": p,
                "avg_offer_acceptance_rate": round(v["total_rate"] / v["count"], 3),
                "total_offers": v["total_offers"],
                "total_hires": v["total_hires"],
            })
    return {"data": result}


@router.get("/conversion-funnel")
def conversion_funnel(period: Optional[str] = Query(None), org: Optional[str] = Query(None)):
    data = get_store().get("interview_metrics", [])
    if period:
        data = [m for m in data if m["period"].lower() == period.lower()]
    if org:
        data = [m for m in data if m["org"].lower() == org.lower()]
    totals = {"screens": 0, "onsites": 0, "offers": 0, "hires": 0}
    for m in data:
        totals["screens"] += m["total_screens"]
        totals["onsites"] += m["total_onsites"]
        totals["offers"] += m["total_offers"]
        totals["hires"] += m["total_hires"]
    s = totals["screens"]
    return {
        "period": period or "all",
        "org": org or "all",
        "funnel": {
            "screens": totals["screens"],
            "onsites": totals["onsites"],
            "offers": totals["offers"],
            "hires": totals["hires"],
        },
        "conversion_rates": {
            "screen_to_onsite": round(totals["onsites"] / s, 3) if s else 0,
            "onsite_to_offer": round(totals["offers"] / max(1, totals["onsites"]), 3),
            "offer_to_hire": round(totals["hires"] / max(1, totals["offers"]), 3),
            "overall": round(totals["hires"] / s, 3) if s else 0,
        },
    }
