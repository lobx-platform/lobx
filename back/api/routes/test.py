"""Test routes: /api/test/* REST endpoints for external testing without WebSocket"""

from fastapi import APIRouter, HTTPException, Request

from core.data_models import TradingParameters, TraderRole
from core.trader_manager import TraderManager
from ..shared import base_settings, market_handler
from utils.api_responses import success

router = APIRouter()


@router.post("/api/test/place_order")
async def test_place_order(request: Request):
    """Place order via REST (bypasses WebSocket). Body: {trader_id, type, price, amount}"""
    data = await request.json()
    trader_id = data.get("trader_id")
    order_type = data.get("type")
    price = data.get("price")
    amount = data.get("amount", 1)

    if not all([trader_id, order_type is not None, price]):
        raise HTTPException(400, "Missing: trader_id, type, or price")

    trader_manager = market_handler.get_trader_manager_by_trader_id(trader_id)
    if not trader_manager:
        raise HTTPException(404, "Trader not in active session")

    trader = trader_manager.get_trader(trader_id)
    if not trader:
        raise HTTPException(404, "Trader not found")

    order_id = await trader.post_new_order(amount, price, order_type)
    return success(order_id=order_id)


@router.post("/api/test/cancel_order")
async def test_cancel_order(request: Request):
    """Cancel order via REST. Body: {trader_id, order_id}"""
    data = await request.json()
    trader_id = data.get("trader_id")
    order_id = data.get("order_id")

    if not all([trader_id, order_id]):
        raise HTTPException(400, "Missing: trader_id or order_id")

    trader_manager = market_handler.get_trader_manager_by_trader_id(trader_id)
    if not trader_manager:
        raise HTTPException(404, "Trader not found")

    trader = trader_manager.get_trader(trader_id)
    if not trader:
        raise HTTPException(404, "Trader not found")

    await trader.send_cancel_order_request(order_id)
    return success(order_id=order_id)


@router.get("/api/test/session_info/{trader_id}")
async def test_get_session_info(trader_id: str):
    """Get session info for a trader (used to find log files)"""
    session_id = market_handler.trader_to_market_lookup.get(trader_id)
    if not session_id:
        raise HTTPException(404, "Trader not in active session")
    return success(data={"session_id": session_id, "trader_id": trader_id, "log_file": f"logs/{session_id}.log"})


@router.get("/api/test/trader_inventory/{trader_id}")
async def test_get_trader_inventory(trader_id: str):
    """Get detailed inventory info for a trader"""
    trader_manager = market_handler.get_trader_manager_by_trader_id(trader_id)
    if not trader_manager:
        raise HTTPException(404, "Trader not in active session")

    trader = trader_manager.get_trader(trader_id)
    if not trader:
        raise HTTPException(404, "Trader not found")

    return success(data={
        "trader_id": trader_id, "trader_type": trader.trader_type,
        "initial_shares": trader.initial_shares, "initial_cash": trader.initial_cash,
        "current_shares": trader.shares, "current_cash": trader.cash,
        "available_shares": trader.get_available_shares(), "available_cash": trader.get_available_cash(),
        "active_orders": len(trader.orders), "filled_orders": len(trader.filled_orders),
        "goal": trader.goal, "goal_progress": trader.goal_progress,
        "negative_inventory": trader.shares < 0, "negative_cash": trader.cash < 0,
    })


@router.post("/api/test/verify_inventory_constraint")
async def test_verify_inventory_constraint(request: Request):
    """Test endpoint to verify inventory constraint is working."""
    data = await request.json()
    trader_id = data.get("trader_id")
    price = data.get("price", 100)

    if not trader_id:
        raise HTTPException(400, "Missing trader_id")

    trader_manager = market_handler.get_trader_manager_by_trader_id(trader_id)
    if not trader_manager:
        raise HTTPException(404, "Trader not in active session")

    trader = trader_manager.get_trader(trader_id)
    if not trader:
        raise HTTPException(404, "Trader not found")

    current_shares = trader.shares
    available_shares = trader.get_available_shares()
    amount = data.get("amount", available_shares + 1)

    from core.data_models import OrderType
    order_id = await trader.post_new_order(amount, price, OrderType.ASK)

    return success(test_result={
        "order_accepted": order_id is not None, "order_id": order_id,
        "constraint_working": order_id is None,
        "shares_before": current_shares, "available_shares": available_shares,
        "attempted_sell_amount": amount,
        "message": "Inventory constraint is WORKING correctly" if order_id is None else "WARNING: Order was accepted despite insufficient shares!"
    })


@router.post("/api/test/create_test_session")
async def create_test_session(request: Request):
    """Create a standalone test session with a mock human trader for inventory testing."""
    data = await request.json() if request.headers.get("content-type") == "application/json" else {}
    initial_shares = data.get("initial_shares", 10)
    initial_cash = data.get("initial_cash", 10000)

    import time as time_module
    import uuid

    test_session_id = f"TEST_SESSION_{int(time_module.time())}_{uuid.uuid4().hex[:8]}"
    test_username = f"test_user_{uuid.uuid4().hex[:8]}"
    trader_id = f"HUMAN_{test_username}"

    params_dict = dict(base_settings) if base_settings else {}
    params_dict["initial_stocks"] = initial_shares
    params_dict["initial_cash"] = initial_cash
    params_dict["trading_day_duration"] = 5.0
    params_dict["num_noise_traders"] = 1
    params_dict["num_informed_traders"] = 0
    params_dict["predefined_goals"] = [0]

    params = TradingParameters(**params_dict)
    manager = TraderManager(params, market_id=test_session_id)
    market_handler.trader_managers[test_session_id] = manager

    await manager.add_human_trader(test_username, TraderRole.SPECULATOR, goal=0)

    market_handler.trader_to_market_lookup[trader_id] = test_session_id
    market_handler.active_users[test_session_id] = {test_username}
    market_handler.market_ready_traders[test_session_id] = {trader_id}

    market_handler.session_manager.user_sessions[test_username] = test_session_id
    market_handler.session_manager.active_markets[test_session_id] = manager

    await manager.trading_market.initialize()
    manager.trading_market.trading_started = True
    await manager.trading_market.start_trading()

    trader = manager.get_trader(trader_id)

    return success(
        test_session={
            "session_id": test_session_id, "trader_id": trader_id,
            "initial_shares": trader.initial_shares if trader else initial_shares,
            "initial_cash": trader.initial_cash if trader else initial_cash,
            "current_shares": trader.shares if trader else None,
            "current_cash": trader.cash if trader else None,
        },
        usage={
            "check_inventory": f"GET /api/test/trader_inventory/{trader_id}",
            "place_order": f"POST /api/test/place_order with {{trader_id: '{trader_id}', type: 0 or 1, price: X, amount: Y}}",
            "verify_constraint": f"POST /api/test/verify_inventory_constraint with {{trader_id: '{trader_id}'}}",
        }
    )
