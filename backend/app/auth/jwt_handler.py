from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from passlib.context import CryptContext

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Demo users — in prod replace with corporate SSO / OIDC provider lookup
USERS_DB = {
    "recruiter1": {
        "user_id": "USR-001",
        "username": "recruiter1",
        "hashed_password": pwd_ctx.hash("password123"),
        "role": "recruiter",
        "full_name": "Priya Sharma",
        "email": "priya.sharma@amazon.com",
    },
    "hm_alice": {
        "user_id": "USR-002",
        "username": "hm_alice",
        "hashed_password": pwd_ctx.hash("password123"),
        "role": "hiring_manager",
        "full_name": "Alice Johnson",
        "email": "alice.johnson@amazon.com",
        "employee_id": "EMP-0005",
    },
    "admin": {
        "user_id": "USR-003",
        "username": "admin",
        "hashed_password": pwd_ctx.hash("admin123"),
        "role": "admin",
        "full_name": "HR Admin",
        "email": "hr-admin@amazon.com",
    },
    "recruiter2": {
        "user_id": "USR-004",
        "username": "recruiter2",
        "hashed_password": pwd_ctx.hash("password123"),
        "role": "recruiter",
        "full_name": "Marcus Thompson",
        "email": "marcus.thompson@amazon.com",
    },
}


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_ctx.verify(plain, hashed)


def authenticate_user(username: str, password: str) -> dict | None:
    user = USERS_DB.get(username)
    if not user or not verify_password(password, user["hashed_password"]):
        return None
    return user


def create_token(user: dict, secret: str, algorithm: str, expire_minutes: int) -> str:
    payload = {
        "sub": user["user_id"],
        "username": user["username"],
        "role": user["role"],
        "full_name": user["full_name"],
        "email": user["email"],
        "exp": datetime.now(timezone.utc) + timedelta(minutes=expire_minutes),
    }
    if "employee_id" in user:
        payload["employee_id"] = user["employee_id"]
    return jwt.encode(payload, secret, algorithm=algorithm)


def decode_token(token: str, secret: str, algorithm: str) -> dict:
    try:
        return jwt.decode(token, secret, algorithms=[algorithm])
    except JWTError as e:
        raise ValueError(f"Invalid token: {e}")
