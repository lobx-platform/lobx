import os
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer
from .lab_auth import LAB_TOKENS, lab_trader_map

security = HTTPBearer(auto_error=False)

# Admin password from environment (default "admin" for dev)
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin")

# Store authenticated users
authenticated_users = {}


def extract_gmail_username(email):
    return email.split('@')[0] if '@' in email else email


async def get_current_user(request: Request):
    """Authenticate user via Lab token or admin Bearer token."""
    # Check for lab token in Authorization header
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Lab '):
        lab_token = auth_header.split('Lab ', 1)[1]
        if lab_token in LAB_TOKENS:
            from .lab_auth import validate_lab_token
            is_valid, lab_user = validate_lab_token(lab_token)
            if is_valid:
                lab_trader_map[lab_user['trader_id']] = lab_user
                return lab_user

    # Check if this is a request for a specific trader (by path)
    path = request.url.path
    trader_id = None
    if path.startswith("/trader/"):
        parts = path.split("/")
        if len(parts) > 2:
            trader_id = parts[2]
    elif path.startswith("/trader_info/"):
        trader_id = path.split("/")[-1]

    # Check if this is a lab user by trader_id
    if trader_id and trader_id in lab_trader_map:
        return lab_trader_map[trader_id]

    # Check if we have it in authenticated_users
    if trader_id and trader_id.startswith("HUMAN_"):
        gmail_username = trader_id.split('_', 1)[1]
        if gmail_username in authenticated_users:
            return authenticated_users[gmail_username]

    # Check for Prolific users by trader_id in authenticated_users
    if trader_id and trader_id.startswith("HUMAN_PROLIFIC_"):
        prolific_username = trader_id.split('_', 1)[1]  # "PROLIFIC_xxx"
        if prolific_username in authenticated_users:
            return authenticated_users[prolific_username]

    # Check for admin Bearer token
    if auth_header.startswith('Bearer '):
        token = auth_header.split('Bearer ')[1]
        if token == ADMIN_PASSWORD:
            return {"username": "admin", "gmail_username": "admin", "is_admin": True}

    if not auth_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No Authorization header found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_admin_user(request: Request):
    """Accept EITHER admin password as Bearer token OR existing auth flow."""
    auth_header = request.headers.get('Authorization', '')

    # Fast path: admin password as Bearer token
    if auth_header.startswith('Bearer '):
        token = auth_header.split('Bearer ')[1]
        if token == ADMIN_PASSWORD:
            return {"username": "admin", "gmail_username": "admin", "is_admin": True}

    # Fall back to full auth flow
    current_user = await get_current_user(request)
    if not current_user.get('is_admin', False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return current_user
