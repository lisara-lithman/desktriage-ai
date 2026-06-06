"""
app/auth/dependencies.py
Reusable FastAPI security dependency.
Decodes the JWT from the Authorization header and returns the authenticated user document.
"""

import os
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.database.connection import db

SECRET_KEY = os.getenv("JWT_SECRET")
ALGORITHM  = "HS256"

# This tells FastAPI to look for a Bearer token in the Authorization header
bearer_scheme = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)
) -> dict:
    """
    Security guard for all protected routes.

    1. Extracts the raw JWT string from the Authorization: Bearer header
    2. Decodes and verifies the token signature using our JWT_SECRET
    3. Pulls the username from the payload
    4. Fetches and returns the full user document from MongoDB
    5. Raises 401 if the token is missing, expired, or tampered with
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired session. Please log in again.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        token   = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("username")

        if username is None:
            raise credentials_exception

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise credentials_exception

    # Fetch the live user document from the database
    user = await db.users.find_one({"username": username})
    if user is None:
        raise credentials_exception

    return user


async def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """
    Additional guard layer — only allows admin_global or admin_dept roles.
    Use this on top of get_current_user for admin-only routes.
    """
    if current_user.get("role") not in ("admin_global", "admin_dept"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Administrator privileges required."
        )
    return current_user
