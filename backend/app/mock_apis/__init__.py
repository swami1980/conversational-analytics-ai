from .requisitions import router as requisitions_router
from .candidates import router as candidates_router
from .employees import router as employees_router
from .pending_starts import router as pending_starts_router
from .interview_events import router as interview_events_router
from .interview_metrics import router as interview_metrics_router
from .historical_data import router as historical_data_router

__all__ = [
    "requisitions_router",
    "candidates_router",
    "employees_router",
    "pending_starts_router",
    "interview_events_router",
    "interview_metrics_router",
    "historical_data_router",
]
