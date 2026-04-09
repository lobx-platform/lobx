"""Auth routes: /user/login, /admin/login, /session/status, /session/reset-for-new-market"""

import os
from fastapi import APIRouter, HTTPException, Depends, Request
from core.data_models import TradingParameters
from ..auth import get_current_user, ADMIN_PASSWORD, trader_registry
from ..shared import base_settings, market_handler, get_historical_markets_count
from utils.api_responses import success

router = APIRouter()


@router.post("/user/login")
async def user_login(request: Request):
    # Check for lab token first (accept both ?LAB= and legacy ?LAB_TOKEN=)
    lab_token = request.query_params.get('LAB') or request.query_params.get('LAB_TOKEN')
    if lab_token:
        from ..lab_auth import validate_lab_token, lab_trader_map
        is_valid, lab_user = validate_lab_token(lab_token)
        if not is_valid:
            raise HTTPException(status_code=401, detail="Invalid or expired lab token")
        gmail_username = lab_user['gmail_username']
        trader_id = lab_user['trader_id']
        treatment_group = lab_user.get('treatment_group')
        lab_trader_map[trader_id] = lab_user
        trader_registry[trader_id] = lab_user
        await market_handler.remove_user_from_session(gmail_username)
        # Register treatment group for waiting room assignment
        if treatment_group is not None:
            market_handler.session_manager.user_treatment_groups[gmail_username] = treatment_group
        return success(
            message="Lab login successful",
            data={"trader_id": trader_id, "username": gmail_username, "is_admin": False,
                  "is_lab": True, "treatment_group": treatment_group}
        )

    # Check for Prolific params
    prolific_pid = request.query_params.get('PROLIFIC_PID')
    if prolific_pid:
        study_id = request.query_params.get('STUDY_ID', '')
        session_id = request.query_params.get('SESSION_ID', '')
        treatment_group = request.query_params.get('TREATMENT')
        gmail_username = f"PROLIFIC_{prolific_pid}"
        trader_id = f"HUMAN_{gmail_username}"
        await market_handler.remove_user_from_session(gmail_username)
        # Register treatment group if provided (e.g. &TREATMENT=0)
        if treatment_group is not None:
            try:
                market_handler.session_manager.user_treatment_groups[gmail_username] = int(treatment_group)
            except ValueError:
                pass
        prolific_user = {"gmail_username": gmail_username, "trader_id": trader_id,
                         "is_admin": False, "is_prolific": True, "prolific_pid": prolific_pid}
        trader_registry[trader_id] = prolific_user
        return success(
            message="Prolific login successful",
            data={"trader_id": trader_id, "username": gmail_username, "is_admin": False,
                  "is_prolific": True, "prolific_pid": prolific_pid,
                  "study_id": study_id, "session_id": session_id,
                  "treatment_group": int(treatment_group) if treatment_group is not None else None}
        )

    raise HTTPException(status_code=401, detail="Invalid authentication method")


@router.post("/admin/login")
async def admin_login(request: Request):
    """Admin login with password or Firebase token (transitional)."""
    body = {}
    try:
        body = await request.json()
    except Exception:
        pass

    password = body.get("password")
    if password and password == ADMIN_PASSWORD:
        return success(message="Admin login successful", data={"username": "admin", "is_admin": True})

    raise HTTPException(status_code=401, detail="Invalid authentication method")


@router.get("/session/status")
async def get_session_status(request: Request, current_user: dict = Depends(get_current_user)):
    """Get the current session status for the authenticated user."""
    gmail_username = current_user['gmail_username']
    trader_id = f"HUMAN_{gmail_username}"
    is_admin = current_user.get('is_admin', False)

    try:
        merged_params = TradingParameters(**(base_settings or {}))
    except Exception:
        merged_params = TradingParameters()

    session_status = market_handler.get_session_status_by_trader_id(trader_id)
    historical_markets_count = get_historical_markets_count(gmail_username)
    max_markets = merged_params.max_markets_per_human

    status = "authenticated"
    market_id = None
    onboarding_step = 0

    if session_status.get("status") == "active":
        status = "trading"
        trader_manager = market_handler.get_trader_manager_by_trader_id(trader_id)
        if trader_manager:
            market_id = trader_manager.trading_market.id
    elif session_status.get("status") == "finished":
        status = "summary"
        market_id = session_status.get("market_id")
    elif session_status.get("status") == "waiting":
        status = "waiting"
    elif historical_markets_count >= max_markets and not is_admin:
        status = "complete"
    else:
        status = "onboarding"

    return success(data={
        "status": status, "trader_id": trader_id, "market_id": market_id,
        "onboarding_step": onboarding_step, "markets_completed": historical_markets_count,
        "max_markets": max_markets, "is_admin": is_admin
    })


@router.post("/session/reset-for-new-market")
async def reset_session_for_new_market(request: Request, current_user: dict = Depends(get_current_user)):
    """Reset user's session to prepare for a new market."""
    gmail_username = current_user['gmail_username']
    await market_handler.remove_user_from_session(gmail_username)
    await market_handler.cleanup_finished_markets()
    return success(message="Session reset for new market", data={"username": gmail_username})


