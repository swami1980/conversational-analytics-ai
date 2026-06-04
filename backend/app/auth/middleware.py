from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from app.auth.jwt_handler import decode_token
from app.config import get_settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")

ROLE_HIERARCHY = {"admin": 3, "recruiter": 2, "hiring_manager": 1}


def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    settings = get_settings()
    try:
        payload = decode_token(token, settings.jwt_secret_key, settings.jwt_algorithm)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


def require_role(*allowed_roles: str):
    """Decorator factory — enforces role-based access (mirrors Bindle permission check)."""
    def _check(user: dict = Depends(get_current_user)) -> dict:
        if user.get("role") not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user.get('role')}' is not authorized for this resource",
            )
        return user
    return _check


def apply_rbac_filter(data: list[dict], user: dict, id_field: str = "hiring_manager_id") -> list[dict]:
    """
    Hiring managers see only their own records.
    Recruiters and admins see everything.
    Mirrors the Bindle-scoped data access pattern.
    """
    if user.get("role") == "hiring_manager":
        emp_id = user.get("employee_id")
        if emp_id:
            return [r for r in data if r.get(id_field) == emp_id]
    return data
