# Data Guide — What Each Dataset Contains

## Requisitions Data
Contains all job openings across the company. Each record represents one approved headcount slot.

Key fields:
- req_id — unique identifier e.g. REQ-0001
- job_family — type of role e.g. SDE, SDM, TPM
- level — seniority e.g. L4, L5, L6, L7
- location — where the role is based e.g. Seattle, NYC, Bangalore
- org — the business unit e.g. AWS, Prime Video, Alexa & Echo
- team — the specific team within the org e.g. EC2, Sponsored Products
- status — Open, Closed, or On Hold
- headcount — number of people approved to hire against this req
- days_open — how many days the req has been open
- target_start_date — when the hire is expected to join
- bar_raiser_required — whether a Bar Raiser interview is mandatory

Use this data to answer: how many open reqs, which reqs are at risk, who owns which reqs, headcount by org.

## Candidates Data
Contains every candidate who has applied or been sourced for a req.

Key fields:
- candidate_id — unique identifier e.g. CAND-0001
- req_id — the req this candidate is applying for
- current_stage — where they are in the pipeline
- source — External, Internal, Agency, or Referral
- applied_date — when they entered the pipeline
- days_in_pipeline — how long they have been in the process
- level_applied — the level they are interviewing for
- location_preference — where they want to work
- gender — used for diversity reporting

Use this data to answer: pipeline health by stage, sourcing mix, candidates near offer, diversity breakdown, stuck candidates.

## Employees Data
Contains the current employee roster across all orgs.

Key fields:
- employee_id — unique identifier e.g. EMP-0001
- job_family and level — current role and seniority
- org and team — where they work
- manager_id — their direct manager
- hire_date and tenure_years — when they joined and how long they have been here
- status — Active or Departed
- departure_reason — Resignation, Termination, Retirement, Transfer, or Contract End

Use this data to answer: total headcount, headcount by org or level, attrition rate, which employees left and why.

## Pending Starts Data
Contains accepted candidates who have not yet started.

Key fields:
- pending_start_id — unique identifier e.g. PS-0001
- start_date — their confirmed first day
- status — Confirmed, Pending, or Deferred
- laptop_provisioned — whether IT has set up their laptop
- badge_requested — whether their access badge has been ordered

Use this data to answer: who is joining soon, are there onboarding risks, how many starts by org or month.

## Interview Events Data
Contains individual interview sessions linked to candidates and reqs.

Key fields:
- event_id — unique identifier e.g. EVT-0001
- event_type — Phone Screen, Bar Raiser, Virtual Onsite, or Loop
- scheduled_date — when the interview is or was
- outcome — Passed, Failed, Pending, or No Show
- feedback_submitted — whether the interviewer has filed feedback
- is_bar_raiser_session — whether this is a Bar Raiser interview

Use this data to answer: upcoming interviews, Bar Raiser schedule, missing feedback, interview outcomes by org.

## Interview Metrics Data
Contains pre-aggregated funnel metrics by org, job family, and quarter.

Key fields:
- period — the quarter e.g. Q1 2025, Q2 2025
- org and job_family — what the metrics apply to
- avg_time_to_hire_days — average days from req open to offer accepted
- conversion_rate_screen_to_onsite — percentage of screened candidates who reach onsite
- conversion_rate_onsite_to_offer — percentage of onsite candidates who receive an offer
- offer_acceptance_rate — percentage of offers accepted
- total_screens, total_onsites, total_offers, total_hires — raw volumes

Use this data to answer: time to hire trends, offer acceptance trends, funnel conversion rates, period over period comparisons.

## Historical Data
Contains quarterly headcount and hiring snapshots by org.

Key fields:
- period — the quarter e.g. Q1 2024
- headcount_start and headcount_end — headcount at start and end of the quarter
- new_hires — people who joined that quarter
- attrition_count and attrition_rate — people who left
- promotions, transfers_in, transfers_out — internal movements
- hiring_plan — the approved hiring target
- plan_attainment — ratio of actual hires to plan

Use this data to answer: headcount growth trends, hiring velocity vs plan, attrition trends over time, org growth trajectories.
