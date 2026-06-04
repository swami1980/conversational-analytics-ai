from fastapi import APIRouter, Query
from typing import Optional
from app.seed_data import get_store

router = APIRouter(prefix="/internal/v1/candidates", tags=["Candidate Pipeline Mock API"])

ACTIVE_STAGES = [
    "Phone Screen Scheduled", "Phone Screen Completed",
    "Onsite Scheduled", "Onsite Completed", "Offer Extended",
]


@router.get("")
def list_candidates(
    req_id: Optional[str] = Query(None),
    current_stage: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    org: Optional[str] = Query(None),
    job_family: Optional[str] = Query(None),
    level_applied: Optional[str] = Query(None),
    hiring_manager_id: Optional[str] = Query(None),
    recruiter_id: Optional[str] = Query(None),
    location_preference: Optional[str] = Query(None),
    days_in_pipeline_gt: Optional[int] = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0),
):
    data = get_store().get("candidates", [])
    if req_id:
        data = [c for c in data if c["req_id"] == req_id]
    if current_stage:
        data = [c for c in data if c["current_stage"].lower() == current_stage.lower()]
    if source:
        data = [c for c in data if c["source"].lower() == source.lower()]
    if org:
        data = [c for c in data if c["org"].lower() == org.lower()]
    if job_family:
        data = [c for c in data if c["job_family"].lower() == job_family.lower()]
    if level_applied:
        data = [c for c in data if c["level_applied"].lower() == level_applied.lower()]
    if hiring_manager_id:
        data = [c for c in data if c["hiring_manager_id"] == hiring_manager_id]
    if recruiter_id:
        data = [c for c in data if c["recruiter_id"] == recruiter_id]
    if location_preference:
        data = [c for c in data if c["location_preference"].lower() == location_preference.lower()]
    if days_in_pipeline_gt is not None:
        data = [c for c in data if c["days_in_pipeline"] > days_in_pipeline_gt]
    total = len(data)
    return {"total": total, "offset": offset, "limit": limit, "data": data[offset: offset + limit]}


@router.get("/pipeline/summary")
def pipeline_summary(org: Optional[str] = Query(None), job_family: Optional[str] = Query(None)):
    data = get_store().get("candidates", [])
    if org:
        data = [c for c in data if c["org"].lower() == org.lower()]
    if job_family:
        data = [c for c in data if c["job_family"].lower() == job_family.lower()]
    stage_counts: dict = {}
    for c in data:
        s = c["current_stage"]
        stage_counts[s] = stage_counts.get(s, 0) + 1
    source_counts: dict = {}
    for c in data:
        s = c["source"]
        source_counts[s] = source_counts.get(s, 0) + 1
    return {
        "total_candidates": len(data),
        "by_stage": stage_counts,
        "by_source": source_counts,
        "active_in_pipeline": sum(1 for c in data if c["current_stage"] in ACTIVE_STAGES),
    }


@router.get("/pipeline/near-offer")
def near_offer(limit: int = Query(20)):
    data = get_store().get("candidates", [])
    near = [c for c in data if c["current_stage"] in ("Onsite Completed", "Offer Extended")]
    near.sort(key=lambda c: c["days_in_pipeline"], reverse=True)
    return {"total": len(near), "data": near[:limit]}


@router.get("/{candidate_id}")
def get_candidate(candidate_id: str):
    data = get_store().get("candidates", [])
    for c in data:
        if c["candidate_id"] == candidate_id:
            return c
    return {"error": f"Candidate {candidate_id} not found"}
