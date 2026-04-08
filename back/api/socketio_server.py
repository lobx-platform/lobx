"""
Socket.IO server — replaces raw WebSocket for real-time trading communication.

Events:
  connect       — authenticate via auth dict (lab_token / admin_token)
  join_market   — join a Socket.IO room by market_id
  place_order   — human places an order
  cancel_order  — human cancels an order
  mark_ready    — participant signals readiness
  disconnect    — cleanup
"""

import asyncio
import json
from typing import Dict

import socketio

from .auth import extract_gmail_username
from .lab_auth import validate_lab_token, lab_trader_map
from .shared import (
    base_settings,
    market_handler,
    trader_locks,
    sanitize_websocket_message,
)
from core.data_models import TradingParameters
from utils.utils import setup_custom_logger

logger = setup_custom_logger(__name__)

# ── Socket.IO server instance ────────────────────────────────────────────────

import os

sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",
    logger=False,
    engineio_logger=False,
)

# The socketio_path on ASGIApp must account for uvicorn --root-path
_root_path = os.environ.get("ROOT_PATH", "/api")

# Mapping: sid -> user context
_sessions: Dict[str, dict] = {}


# ── Helpers ──────────────────────────────────────────────────────────────────

def _authenticate(auth: dict) -> dict | None:
    """Return user dict or None if auth fails."""
    if not auth:
        return None

    # Lab token
    lab_token = auth.get("lab_token")
    if lab_token and lab_token.startswith("lab_"):
        is_valid, lab_user = validate_lab_token(lab_token)
        if is_valid:
            lab_trader_map[lab_user["trader_id"]] = lab_user
            return lab_user

    # Admin token (Bearer style — the frontend sends the raw token)
    admin_token = auth.get("admin_token")
    if admin_token:
        import os
        from .auth import ADMIN_PASSWORD
        if admin_token == ADMIN_PASSWORD:
            return {
                "gmail_username": "admin",
                "trader_id": "HUMAN_admin",
                "is_admin": True,
            }

    # Prolific user — authenticate via trader_id lookup in authenticated_users
    prolific_pid = auth.get("prolific_pid")
    if prolific_pid:
        from .auth import authenticated_users
        gmail_username = f"PROLIFIC_{prolific_pid}"
        if gmail_username in authenticated_users:
            return authenticated_users[gmail_username]
        # Auto-create if not found (Prolific users are pre-validated via HTTP login)
        trader_id = f"HUMAN_{gmail_username}"
        return {
            "gmail_username": gmail_username,
            "trader_id": trader_id,
            "is_admin": False,
            "is_prolific": True,
        }

    return None


async def _get_or_create_trader_lock(trader_id: str) -> asyncio.Lock:
    if trader_id not in trader_locks:
        trader_locks[trader_id] = asyncio.Lock()
    return trader_locks[trader_id]


# ── Event handlers ───────────────────────────────────────────────────────────

@sio.event
async def connect(sid, environ, auth):
    """Authenticate on connect.  auth = {lab_token: ...} or {admin_token: ...}."""
    user = _authenticate(auth)
    if not user:
        logger.warning(f"[SIO] connection refused for sid={sid}")
        raise socketio.exceptions.ConnectionRefusedError("authentication failed")

    _sessions[sid] = {
        "gmail_username": user["gmail_username"],
        "trader_id": user.get("trader_id", f"HUMAN_{user['gmail_username']}"),
        "is_admin": user.get("is_admin", False),
        "market_id": None,
    }
    logger.info(f"[SIO] connected sid={sid} user={user['gmail_username']}")


@sio.event
async def disconnect(sid):
    ctx = _sessions.pop(sid, None)
    if not ctx:
        return
    market_id = ctx.get("market_id")
    gmail_username = ctx["gmail_username"]
    if market_id:
        await sio.leave_room(sid, market_id)
        # broadcast updated trader count to the room
        await _broadcast_trader_count(market_id)
    logger.info(f"[SIO] disconnected sid={sid} user={gmail_username}")


@sio.event
async def join_market(sid, data):
    """Client requests to join a market room.

    data: { market_id: str }  — or the server can auto-resolve it.
    """
    ctx = _sessions.get(sid)
    if not ctx:
        return

    trader_id = ctx["trader_id"]
    gmail_username = ctx["gmail_username"]

    # Resolve market_id from trader's active session
    session_status = market_handler.get_session_status_by_trader_id(trader_id)
    status = session_status.get("status")

    if status == "not_found":
        await sio.emit("error", {"message": "Not in any session"}, to=sid)
        return

    # If still waiting, send waiting status and poll until active
    if status == "waiting":
        await sio.emit("session_waiting", {
            "status": "waiting",
            "message": "Waiting for other traders to join",
            "isWaitingForOthers": True,
        }, to=sid)

        # Poll for up to 60 s
        for _ in range(60):
            new_status = market_handler.get_session_status_by_trader_id(trader_id)
            if new_status.get("status") == "active":
                break
            await asyncio.sleep(1)
        else:
            await sio.emit("error", {"message": "Timeout waiting for market"}, to=sid)
            return

    # Resolve trader manager
    trader_manager = None
    for _ in range(10):
        trader_manager = market_handler.get_trader_manager_by_trader_id(trader_id)
        if trader_manager:
            break
        await asyncio.sleep(0.5)

    if not trader_manager:
        await sio.emit("error", {"message": "No trader manager found"}, to=sid)
        return

    market_id = market_handler.trader_to_market_lookup.get(trader_id)
    if not market_id:
        await sio.emit("error", {"message": "Market ID not found"}, to=sid)
        return

    ctx["market_id"] = market_id

    trader = trader_manager.get_trader(trader_id)
    if not trader:
        await sio.emit("error", {"message": "Trader not found in market"}, to=sid)
        return

    # Join Socket.IO room
    await sio.enter_room(sid, market_id)
    market_handler.add_user_to_market(gmail_username, market_id)

    # Send initial trader count
    count_msg = sanitize_websocket_message({
        "type": "trader_count_update",
        "data": {
            "current_human_traders": len(market_handler.active_users.get(market_id, set())),
            "expected_human_traders": len(trader_manager.params.predefined_goals),
            "market_id": market_id,
        },
    })
    await sio.emit("trader_count_update", count_msg["data"], to=sid)

    # Wait for trading to start (launch() is a background task)
    for _ in range(30):
        if trader_manager.trading_market.trading_started:
            break
        await asyncio.sleep(0.5)

    # Connect the trader to its Socket.IO bridge
    await trader.connect_to_socketio(sio, sid, market_id)

    # Start the time-update loop for this client
    asyncio.create_task(_time_update_loop(sid, trader_manager, market_id))

    logger.info(f"[SIO] {trader_id} joined room {market_id}")


@sio.event
async def place_order(sid, data):
    """Human places an order.  data: {type: 1/-1, price: int, amount: int}"""
    ctx = _sessions.get(sid)
    if not ctx:
        return

    trader_id = ctx["trader_id"]
    trader_manager = market_handler.get_trader_manager_by_trader_id(trader_id)
    if not trader_manager:
        return

    trader = trader_manager.get_trader(trader_id)
    if not trader:
        return

    message = json.dumps({"type": "add_order", "data": data})
    lock = await _get_or_create_trader_lock(trader_id)
    async with lock:
        await trader.on_message_from_client(message)


@sio.event
async def cancel_order(sid, data):
    """Human cancels an order.  data: {id: str}"""
    ctx = _sessions.get(sid)
    if not ctx:
        return

    trader_id = ctx["trader_id"]
    trader_manager = market_handler.get_trader_manager_by_trader_id(trader_id)
    if not trader_manager:
        return

    trader = trader_manager.get_trader(trader_id)
    if not trader:
        return

    message = json.dumps({"type": "cancel_order", "data": data})
    await trader.on_message_from_client(message)


@sio.event
async def mark_ready(sid, data=None):
    """Participant signals readiness.  Triggers market start if all ready."""
    ctx = _sessions.get(sid)
    if not ctx:
        return

    trader_id = ctx["trader_id"]
    all_ready = await market_handler.mark_trader_ready_by_trader_id(trader_id)

    if all_ready:
        trader_manager = market_handler.get_trader_manager_by_trader_id(trader_id)
        if trader_manager:
            market_id = market_handler.trader_to_market_lookup.get(trader_id)
            asyncio.create_task(trader_manager.launch())
            await sio.emit("market_started", {"market_id": market_id}, room=market_id)
    else:
        await sio.emit("ready_ack", {"status": "waiting"}, to=sid)


# ── Background loops ─────────────────────────────────────────────────────────

async def _time_update_loop(sid: str, trader_manager, market_id: str):
    """Send periodic time updates to a single client."""
    from datetime import timedelta

    try:
        while sid in _sessions:
            tm = trader_manager.trading_market
            remaining = None
            if tm.trading_started and tm.start_time:
                remaining = max(
                    0,
                    (tm.start_time + timedelta(minutes=tm.duration) - tm.current_time).total_seconds(),
                )

            payload = sanitize_websocket_message({
                "current_time": tm.current_time.isoformat(),
                "is_trading_started": tm.trading_started,
                "remaining_time": remaining,
                "current_human_traders": len(trader_manager.human_traders),
                "expected_human_traders": len(trader_manager.params.predefined_goals),
            })
            await sio.emit("time_update", payload, to=sid)

            if tm.is_finished:
                break
            await asyncio.sleep(1)
    except Exception as e:
        logger.debug(f"[SIO] time loop ended for sid={sid}: {e}")


async def _broadcast_trader_count(market_id: str):
    """Broadcast current trader count to everyone in a room."""
    trader_manager = market_handler.trader_managers.get(market_id)
    if not trader_manager:
        return

    current = len(market_handler.active_users.get(market_id, set()))
    expected = len(trader_manager.params.predefined_goals)

    await sio.emit("trader_count_update", {
        "current_human_traders": current,
        "expected_human_traders": expected,
        "market_id": market_id,
    }, room=market_id)


# ── Public helpers for other modules ─────────────────────────────────────────

async def emit_to_market(market_id: str, event: str, data: dict):
    """Emit an event to all participants in a market room."""
    sanitized = sanitize_websocket_message(data)
    await sio.emit(event, sanitized, room=market_id)


def get_sio():
    """Return the global sio instance (useful for imports)."""
    return sio
