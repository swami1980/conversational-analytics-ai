import random
from datetime import date, timedelta
from typing import Any

random.seed(42)

ORGS = ["AWS", "Amazon Advertising", "Alexa & Echo", "Prime Video",
        "Kindle", "Amazon Logistics", "Amazon Healthcare", "Amazon Fresh"]

TEAMS = {
    "AWS": ["EC2", "S3", "Lambda", "RDS", "CloudFront", "SageMaker", "EKS", "VPC"],
    "Amazon Advertising": ["DSP", "Sponsored Products", "Attribution", "Measurement", "AMC"],
    "Alexa & Echo": ["Alexa AI", "Echo Devices", "Smart Home", "Skills Platform"],
    "Prime Video": ["Streaming Platform", "Content Acquisition", "Live Sports", "Studios Tech"],
    "Kindle": ["Device Software", "Content Delivery", "Reading Experience"],
    "Amazon Logistics": ["Last Mile", "Middle Mile", "AMZL Tech", "Robotics"],
    "Amazon Healthcare": ["Pharmacy Tech", "Clinic Systems", "Health Data"],
    "Amazon Fresh": ["Grocery Tech", "Inventory Systems", "Delivery Experience"],
}

JOB_FAMILIES = {
    "SDE": ["L4", "L5", "L6", "L7"],
    "SDM": ["L6", "L7"],
    "TPM": ["L4", "L5", "L6"],
    "SDET": ["L4", "L5", "L6"],
    "Data Engineer": ["L4", "L5", "L6"],
    "Applied Scientist": ["L5", "L6", "L7"],
    "Research Scientist": ["L6", "L7"],
    "Solutions Architect": ["L5", "L6"],
    "DevOps Engineer": ["L4", "L5"],
}

LOCATIONS = ["Seattle", "NYC", "Austin", "San Francisco", "London",
             "Bangalore", "Vancouver", "Berlin", "Tokyo"]

REQ_STATUSES = ["Open", "Open", "Open", "Closed", "On Hold"]

CANDIDATE_STAGES = [
    "Applied", "Phone Screen Scheduled", "Phone Screen Completed",
    "Onsite Scheduled", "Onsite Completed", "Offer Extended",
    "Offer Accepted", "Offer Declined", "Withdrawn",
]

SOURCES = ["External", "External", "Internal", "Agency", "Referral"]

INTERVIEW_TYPES = ["Phone Screen", "Bar Raiser", "Virtual Onsite", "Loop"]

OUTCOMES = ["Passed", "Failed", "Pending", "No Show"]

PERIODS = ["Q1 2024", "Q2 2024", "Q3 2024", "Q4 2024",
           "Q1 2025", "Q2 2025", "Q3 2025", "Q4 2025"]

FIRST_NAMES = [
    "Priya", "James", "Mei", "Carlos", "Fatima", "Alex", "Neha", "David",
    "Yuki", "Marcus", "Aisha", "Ryan", "Sunita", "Chris", "Wei", "Sarah",
    "Raj", "Emily", "Hassan", "Jennifer", "Kenji", "Amanda", "Arjun", "Lisa",
    "Mohammed", "Rachel", "Sanjay", "Michelle", "Ivan", "Tanya", "Vijay",
    "Katherine", "Omar", "Stephanie", "Rohan", "Nicole", "Akira", "Megan",
    "Benjamin", "Preeti", "Tyler", "Nadia", "Adrian", "Cassandra", "Dmitri",
]

LAST_NAMES = [
    "Sharma", "Johnson", "Chen", "Rodriguez", "Ali", "Kim", "Patel", "Williams",
    "Tanaka", "Thompson", "Ibrahim", "Davis", "Gupta", "Martinez", "Liu", "Wilson",
    "Kumar", "Anderson", "Hassan", "Taylor", "Nakamura", "Brown", "Singh", "Jones",
    "Khalid", "Garcia", "Mehta", "Lee", "Petrov", "Walker", "Reddy", "Hall",
    "Yamamoto", "Young", "Kapoor", "Adams", "Watanabe", "Baker", "Mishra",
]

DEPARTURE_REASONS = ["Resignation", "Termination", "Retirement", "Transfer", "Contract End"]


def _rnd_date(start: date, end: date) -> date:
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))


def _name() -> str:
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"


def _email(name: str) -> str:
    parts = name.lower().split()
    return f"{parts[0]}.{parts[1]}@amazon.com"


def generate_employees(n: int = 80) -> list[dict[str, Any]]:
    employees = []
    today = date.today()
    for i in range(1, n + 1):
        name = _name()
        jf = random.choice(list(JOB_FAMILIES.keys()))
        level = random.choice(JOB_FAMILIES[jf])
        org = random.choice(ORGS)
        hire = _rnd_date(date(2018, 1, 1), date(2024, 6, 1))
        is_active = random.random() > 0.12
        emp = {
            "employee_id": f"EMP-{i:04d}",
            "name": name,
            "email": _email(name),
            "job_family": jf,
            "level": level,
            "location": random.choice(LOCATIONS),
            "org": org,
            "team": random.choice(TEAMS[org]),
            "manager_id": f"EMP-{random.randint(1, max(1, i - 1)):04d}" if i > 1 else None,
            "hire_date": hire.isoformat(),
            "tenure_years": round((today - hire).days / 365, 1),
            "status": "Active" if is_active else "Departed",
            "departure_reason": random.choice(DEPARTURE_REASONS) if not is_active else None,
            "departure_date": _rnd_date(date(2024, 1, 1), today).isoformat() if not is_active else None,
        }
        employees.append(emp)
    return employees


def generate_requisitions(employees: list[dict], n: int = 30) -> list[dict[str, Any]]:
    reqs = []
    today = date.today()
    active_emps = [e for e in employees if e["status"] == "Active"]
    for i in range(1, n + 1):
        jf = random.choice(list(JOB_FAMILIES.keys()))
        level = random.choice(JOB_FAMILIES[jf])
        org = random.choice(ORGS)
        recruiter = random.choice(active_emps)
        hm = random.choice(active_emps)
        status = random.choice(REQ_STATUSES)
        created = _rnd_date(date(2024, 6, 1), today - timedelta(days=7))
        days_open = (today - created).days if status != "Closed" else random.randint(30, 120)
        req = {
            "req_id": f"REQ-{i:04d}",
            "title": f"{jf} {level} - {random.choice(TEAMS[org])}",
            "job_family": jf,
            "level": level,
            "location": random.choice(LOCATIONS),
            "org": org,
            "team": random.choice(TEAMS[org]),
            "status": status,
            "headcount": random.randint(1, 4),
            "recruiter_id": recruiter["employee_id"],
            "recruiter_name": recruiter["name"],
            "hiring_manager_id": hm["employee_id"],
            "hiring_manager_name": hm["name"],
            "target_start_date": (today + timedelta(days=random.randint(30, 120))).isoformat(),
            "created_date": created.isoformat(),
            "days_open": days_open,
            "bar_raiser_required": jf in ("SDE", "SDM", "Applied Scientist", "Research Scientist"),
        }
        reqs.append(req)
    return reqs


def generate_candidates(reqs: list[dict], n: int = 150) -> list[dict[str, Any]]:
    candidates = []
    today = date.today()
    for i in range(1, n + 1):
        req = random.choice(reqs)
        name = _name()
        applied = _rnd_date(date(2024, 8, 1), today - timedelta(days=3))
        stage = random.choice(CANDIDATE_STAGES)
        stage_date = _rnd_date(applied, today)
        cand = {
            "candidate_id": f"CAND-{i:04d}",
            "req_id": req["req_id"],
            "name": name,
            "email": f"{name.lower().replace(' ', '.')}@gmail.com",
            "current_stage": stage,
            "source": random.choice(SOURCES),
            "applied_date": applied.isoformat(),
            "last_updated": stage_date.isoformat(),
            "recruiter_id": req["recruiter_id"],
            "recruiter_name": req["recruiter_name"],
            "hiring_manager_id": req["hiring_manager_id"],
            "hiring_manager_name": req["hiring_manager_name"],
            "level_applied": req["level"],
            "job_family": req["job_family"],
            "location_preference": random.choice(LOCATIONS),
            "org": req["org"],
            "days_in_pipeline": (today - applied).days,
            "gender": random.choice(["Male", "Female", "Non-binary", "Prefer not to say"]),
        }
        candidates.append(cand)
    return candidates


def generate_pending_starts(candidates: list[dict], reqs: list[dict], n: int = 20) -> list[dict[str, Any]]:
    today = date.today()
    accepted = [c for c in candidates if c["current_stage"] == "Offer Accepted"]
    req_map = {r["req_id"]: r for r in reqs}
    starts = []
    pool = accepted[:n] if len(accepted) >= n else accepted
    for i, cand in enumerate(pool, 1):
        req = req_map.get(cand["req_id"], reqs[0])
        start_date = _rnd_date(today + timedelta(days=7), today + timedelta(days=90))
        s = {
            "pending_start_id": f"PS-{i:04d}",
            "candidate_id": cand["candidate_id"],
            "req_id": cand["req_id"],
            "name": cand["name"],
            "job_family": cand["job_family"],
            "level": cand["level_applied"],
            "location": cand["location_preference"],
            "org": req["org"],
            "team": req["team"],
            "start_date": start_date.isoformat(),
            "status": random.choice(["Confirmed", "Confirmed", "Pending", "Deferred"]),
            "hiring_manager_id": req["hiring_manager_id"],
            "hiring_manager_name": req["hiring_manager_name"],
            "laptop_provisioned": random.random() > 0.3,
            "badge_requested": random.random() > 0.2,
        }
        starts.append(s)
    return starts


def generate_interview_events(candidates: list[dict], employees: list[dict], n: int = 200) -> list[dict[str, Any]]:
    today = date.today()
    active_emps = [e for e in employees if e["status"] == "Active"]
    events = []
    active_cands = [c for c in candidates if c["current_stage"] not in ("Applied", "Withdrawn")]
    for i in range(1, n + 1):
        cand = random.choice(active_cands)
        interviewer = random.choice(active_emps)
        scheduled = _rnd_date(date(2024, 9, 1), today + timedelta(days=21))
        is_past = scheduled <= today
        evt = {
            "event_id": f"EVT-{i:04d}",
            "candidate_id": cand["candidate_id"],
            "req_id": cand["req_id"],
            "candidate_name": cand["name"],
            "event_type": random.choice(INTERVIEW_TYPES),
            "interviewer_id": interviewer["employee_id"],
            "interviewer_name": interviewer["name"],
            "scheduled_date": scheduled.isoformat(),
            "duration_minutes": random.choice([45, 60, 90]),
            "outcome": random.choice(OUTCOMES) if is_past else "Pending",
            "feedback_submitted": is_past and random.random() > 0.2,
            "is_bar_raiser_session": random.random() > 0.75,
            "org": cand["org"],
            "job_family": cand["job_family"],
        }
        events.append(evt)

    # Guarantee at least 6 Bar Raiser sessions in the next 14 days
    # so Q12 (BR schedule) always has data regardless of random seed
    br_cands = [c for c in active_cands if c["job_family"] in ("SDE", "SDM", "Applied Scientist")]
    for j in range(6):
        cand = br_cands[j % len(br_cands)]
        interviewer = active_emps[j % len(active_emps)]
        scheduled = today + timedelta(days=j * 2 + 1)  # days 1,3,5,7,9,11
        events.append({
            "event_id": f"EVT-BR-{j+1:03d}",
            "candidate_id": cand["candidate_id"],
            "req_id": cand["req_id"],
            "candidate_name": cand["name"],
            "event_type": "Bar Raiser",
            "interviewer_id": interviewer["employee_id"],
            "interviewer_name": interviewer["name"],
            "scheduled_date": scheduled.isoformat(),
            "duration_minutes": 60,
            "outcome": "Pending",
            "feedback_submitted": False,
            "is_bar_raiser_session": True,
            "org": cand["org"],
            "job_family": cand["job_family"],
        })
    return events


def generate_interview_metrics() -> list[dict[str, Any]]:
    metrics = []
    mid = 1
    for period in PERIODS:
        for org in ORGS:
            for jf in random.sample(list(JOB_FAMILIES.keys()), k=3):
                total_screens = random.randint(20, 80)
                screen_to_onsite = random.uniform(0.35, 0.65)
                total_onsites = int(total_screens * screen_to_onsite)
                onsite_to_offer = random.uniform(0.25, 0.55)
                total_offers = int(total_onsites * onsite_to_offer)
                acceptance_rate = random.uniform(0.70, 0.95)
                total_hires = int(total_offers * acceptance_rate)
                m = {
                    "metric_id": f"MET-{mid:04d}",
                    "period": period,
                    "org": org,
                    "job_family": jf,
                    "avg_time_to_hire_days": random.randint(45, 120),
                    "avg_interviews_per_hire": round(random.uniform(4.5, 8.5), 1),
                    "conversion_rate_screen_to_onsite": round(screen_to_onsite, 3),
                    "conversion_rate_onsite_to_offer": round(onsite_to_offer, 3),
                    "offer_acceptance_rate": round(acceptance_rate, 3),
                    "total_screens": total_screens,
                    "total_onsites": total_onsites,
                    "total_offers": total_offers,
                    "total_hires": total_hires,
                }
                metrics.append(m)
                mid += 1
    return metrics


def generate_historical_data() -> list[dict[str, Any]]:
    records = []
    hid = 1
    headcount_base = {org: random.randint(150, 800) for org in ORGS}
    for period in PERIODS:
        for org in ORGS:
            base = headcount_base[org]
            new_hires = random.randint(10, 60)
            attrition = random.randint(5, 25)
            promotions = random.randint(2, 15)
            transfers_in = random.randint(0, 10)
            transfers_out = random.randint(0, 10)
            end = base + new_hires - attrition + transfers_in - transfers_out
            rec = {
                "history_id": f"HIST-{hid:04d}",
                "period": period,
                "org": org,
                "headcount_start": base,
                "headcount_end": end,
                "new_hires": new_hires,
                "attrition_count": attrition,
                "attrition_rate": round(attrition / base, 3),
                "promotions": promotions,
                "transfers_in": transfers_in,
                "transfers_out": transfers_out,
                "hiring_plan": random.randint(new_hires - 5, new_hires + 10),
                "plan_attainment": round(new_hires / max(1, random.randint(new_hires - 5, new_hires + 10)), 3),
            }
            records.append(rec)
            headcount_base[org] = end
            hid += 1
    return records


def generate_all() -> dict[str, list]:
    employees = generate_employees(80)
    reqs = generate_requisitions(employees, 30)
    candidates = generate_candidates(reqs, 150)
    pending_starts = generate_pending_starts(candidates, reqs, 20)
    interview_events = generate_interview_events(candidates, employees, 200)
    interview_metrics = generate_interview_metrics()
    historical_data = generate_historical_data()
    return {
        "employees": employees,
        "requisitions": reqs,
        "candidates": candidates,
        "pending_starts": pending_starts,
        "interview_events": interview_events,
        "interview_metrics": interview_metrics,
        "historical_data": historical_data,
    }
