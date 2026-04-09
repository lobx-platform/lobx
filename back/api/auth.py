import os
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer
from .lab_auth import validate_lab_token, lab_trader_map

security = HTTPBearer(auto_error=False)

# Admin password from environment (MUST be set in .env or docker-compose)
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

# Unified trader registry: trader_id → user dict
# Both lab and prolific users register here on login.
trader_registry = {}


def extract_gmail_username(email):
    return email.split('@')[0] if '@' in email else email


async def get_current_user(request: Request):
    """Authenticate user via unified Trader token, or admin Bearer token."""
    auth_header = request.headers.get('Authorization', '')

    # Unified: Trader <trader_id>
    if auth_header.startswith('Trader '):
        trader_id = auth_header.split('Trader ', 1)[1]
        if trader_id in trader_registry:
            return trader_registry[trader_id]

    # Legacy: Lab <token> (keep for backward compat)
    if auth_header.startswith('Lab '):
        lab_token = auth_header.split('Lab ', 1)[1]
        is_valid, lab_user = validate_lab_token(lab_token)
        if is_valid:
            trader_registry[lab_user['trader_id']] = lab_user
            return lab_user

    # Path-based lookup (for /trader/<id>/... and /trader_info/<id> routes)
    path = request.url.path
    trader_id = None
    if path.startswith("/trader/"):
        parts = path.split("/")
        if len(parts) > 2:
            trader_id = parts[2]
    elif path.startswith("/trader_info/"):
        trader_id = path.split("/")[-1]

    if trader_id and trader_id in trader_registry:
        return trader_registry[trader_id]

    # Legacy fallback: lab_trader_map
    if trader_id and trader_id in lab_trader_map:
        return lab_trader_map[trader_id]

    # Admin Bearer token
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
