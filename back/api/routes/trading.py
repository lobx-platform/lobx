"""Trading routes: /trading/start, /trader_info/{id}, /trader/{id}/market, /traders/defaults, /market_metrics

WebSocket handler has been replaced by Socket.IO events in api/socketio_server.py.
"""

import asyncio
import io
import os
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Request, Query
from fastapi.responses import JSONResponse, StreamingResponse

from core.trader_manager import TraderManager
from core.data_models import TradingParameters
from ..auth import get_current_user
from ..shared import (
    base_settings, market_handler, accumulated_rewards,
    get_historical_markets_count,
)
from utils.api_responses import success, waiting, not_in_session
from utils.logfiles_analysis import order_book_contruction, calculate_trader_specific_metrics
from utils.calculate_metrics import process_log_file, write_to_csv
from ..random_picker import pick_random_element_new

router = APIRouter()


def get_manager_by_trader(trader_id: str):
    """Get trader manager for trader ID"""
    if trader_id not in market_handler.trader_to_market_lookup:
        return None
    trading_market_id = market_handler.trader_to_market_lookup[trader_id]
    manager = market_handler.trader_managers.get(trading_market_id)
    return manager


def get_trader_info_with_market_data(trader_manager: TraderManager, trader_id: str) -> Dict[str, Any]:
    try:
        trader = trader_manager.get_trader(trader_id)
        if not trader:
            raise HTTPException(status_code=404, detail="Trader not found")

        trader_data = trader.get_trader_params_as_dict()

        if 'all_attributes' not in trader_data:
            trader_data['all_attributes'] = {}

        gmail_username = trader_id.split("HUMAN_")[-1] if trader_id.startswith("HUMAN_") else None

        historical_markets_count = len(market_handler.user_historical_markets.get(gmail_username, set()))

        params = trader_manager.params.model_dump() if trader_manager.params else {}

        admin_users = params.get('admin_users', [])
        is_admin = gmail_username in admin_users if gmail_username else False

        trader_data['all_attributes'].update({
            'historical_markets_count': historical_markets_count,
            'is_admin': is_admin,
            'params': params
        })

        if 'cash' not in trader_data:
            trader_data['cash'] = getattr(trader, 'cash', 0)
        if 'shares' not in trader_data:
            trader_data['shares'] = getattr(trader, 'shares', 0)
        if 'goal' not in trader_data:
            trader_data['goal'] = getattr(trader, 'goal', 0)

        return trader_data

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting trader info: {str(e)}")


@router.get("/traders/defaults")
async def get_trader_defaults():
    schema = TradingParameters.model_json_schema()
    defaults = {
        field: {
            "default": props.get("default"),
            "title": props.get("title"),
            "type": props.get("type"),
            "hint": props.get("description"),
        }
        for field, props in schema.get("properties", {}).items()
    }
    return JSONResponse(content=success(data=defaults))


@router.post("/trading/initiate")
async def create_trading_market(background_tasks: BackgroundTasks, request: Request, current_user: dict = Depends(get_current_user)):
    try:
        merged_params = TradingParameters(**(base_settings or {}))
    except Exception:
        merged_params = TradingParameters()

    gmail_username = current_user['gmail_username']
    trader_id = f"HUMAN_{gmail_username}"

    session_status = market_handler.get_session_status_by_trader_id(trader_id)

    if session_status.get("status") == "not_found":
        return not_in_session(
            "User not in trading session yet",
            data={"trader_id": trader_id, "num_human_traders": len(merged_params.predefined_goals), "isWaitingForOthers": False}
        )

    if session_status.get("status") == "waiting":
        return waiting(
            "Waiting for other traders to join",
            data={"trader_id": trader_id, "num_human_traders": len(merged_params.predefined_goals), "isWaitingForOthers": True}
        )

    trader_manager = market_handler.get_trader_manager_by_trader_id(trader_id)
    if not trader_manager:
        raise HTTPException(status_code=404, detail="No active market found for this user")

    trader_manager.params = merged_params

    return success(
        message="Trading market info retrieved",
        data={"trader_id": trader_id, "traders": list(trader_manager.traders.keys()),
              "human_traders": [t.id for t in trader_manager.human_traders],
              "num_human_traders": len(merged_params.predefined_goals), "isWaitingForOthers": False}
    )


@router.get("/trader_info/{trader_id}")
async def get_trader_info(trader_id: str):
    if not trader_id.startswith("HUMAN_"):
        raise HTTPException(status_code=404, detail="Invalid trader ID")

    username = trader_id[6:]

    session_status = market_handler.get_session_status_by_trader_id(trader_id)

    if session_status.get("status") == "not_found":
        historical_markets_count = len(market_handler.user_historical_markets.get(username, set()))
        params = TradingParameters(**(base_settings or {}))
        trader_data = {
            'cash': params.initial_cash,
            'shares': params.initial_stocks,
            'id': trader_id,
            'all_attributes': {
                'historical_markets_count': historical_markets_count,
                'is_admin': username in ['venvoooo', 'asancetta', 'marjonuzaj', 'fra160756', 'expecon', 'w.wu'],
                'params': base_settings,
                'isWaitingForOthers': False
            }
        }
        return {
            "status": "not_in_session",
            "message": "Trader not in session yet - showing default attributes",
            "data": {**trader_data, "order_book_metrics": {}, "trader_specific_metrics": {}}
        }

    if session_status.get("status") == "waiting":
        historical_markets_count = len(market_handler.user_historical_markets.get(username, set()))
        assigned_cash = session_status.get("cash", 100000)
        assigned_shares = session_status.get("shares", 300)
        assigned_goal = session_status.get("goal", 0)
        trader_data = {
            'cash': assigned_cash, 'shares': assigned_shares, 'goal': assigned_goal,
            'id': trader_id,
            'all_attributes': {
                'historical_markets_count': historical_markets_count,
                'is_admin': username in ['venvoooo', 'asancetta', 'marjonuzaj', 'fra160756', 'expecon', 'w.wu'],
                'params': base_settings,
                'isWaitingForOthers': True
            }
        }
        return {
            "status": "waiting",
            "message": "Trader in session pool, waiting for market to start",
            "data": {**trader_data, "order_book_metrics": {}, "trader_specific_metrics": {}}
        }

    trader_manager = market_handler.get_trader_manager_by_trader_id(trader_id)
    internal_session_id = market_handler.trader_to_market_lookup.get(trader_id)

    if not trader_manager:
        if not internal_session_id:
            raise HTTPException(status_code=404, detail="Trader not found")
        gmail_username = username
        trader_data = {
            "trader_id": trader_id,
            "all_attributes": {
                "is_admin": False,
                "isWaitingForOthers": False,
                "historical_markets_count": len(market_handler.session_manager.user_historical_markets.get(gmail_username, set())),
                "params": {"max_markets_per_human": base_settings.get("max_markets_per_human", 6)},
            },
        }

    try:
        if trader_manager:
            trader_data = get_trader_info_with_market_data(trader_manager, trader_id)
        log_file_path = os.path.join("logs", f"{internal_session_id}.log")

        try:
            if os.path.exists(log_file_path):
                order_book_metrics = order_book_contruction(log_file_path)
                quoted_trader_id = f"'{trader_id}'"
                trader_specific_metrics = order_book_metrics.get(quoted_trader_id, {})
                if not trader_specific_metrics:
                    trader_specific_metrics = order_book_metrics.get(trader_id, {})

                trader_keys_to_exclude = {quoted_trader_id, trader_id}
                general_metrics = {k: v for k, v in order_book_metrics.items() if k not in trader_keys_to_exclude}

                if trader_specific_metrics:
                    trader_goal = trader_data.get('goal', 0)
                    conversion_rate = trader_data.get('conversion_rate', 1)
                    trader_specific_metrics = calculate_trader_specific_metrics(
                        trader_specific_metrics, general_metrics, trader_goal, conversion_rate
                    )
                    if isinstance(trader_specific_metrics.get('Reward'), (int, float)):
                        if trader_id not in accumulated_rewards:
                            accumulated_rewards[trader_id] = {}
                        accumulated_rewards[trader_id][internal_session_id] = trader_specific_metrics['Reward']

                    all_rewards = list(accumulated_rewards.get(trader_id, {}).values())
                    if len(all_rewards) <= 1:
                        trader_specific_metrics['Accumulated_Reward'] = 0
                    else:
                        trader_specific_metrics['Accumulated_Reward'] = pick_random_element_new(all_rewards[1:])
                else:
                    trader_specific_metrics = {
                        'Trades': 0, 'Num_Buy': 0, 'Num_Sell': 0, 'Remaining_Trades': 0,
                        'PnL': 0, 'Reward': 0, 'Accumulated_Reward': 0,
                    }
            else:
                order_book_metrics = {}
                trader_specific_metrics = {}
        except Exception as e:
            print(f"Error processing metrics for trader {trader_id}: {str(e)}")
            order_book_metrics = {}
            trader_specific_metrics = {}

        if 'all_attributes' not in trader_data:
            trader_data['all_attributes'] = {}
        trader_data['all_attributes']['isWaitingForOthers'] = False

        return success(message="Trader found", data={**trader_data, "order_book_metrics": order_book_metrics, "trader_specific_metrics": trader_specific_metrics})

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting trader info: {str(e)}")


@router.get("/trader/{trader_id}/market")
async def get_trader_market(trader_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    gmail_username = current_user.get('gmail_username', '')

    session_status = market_handler.get_session_status_by_trader_id(trader_id)

    if session_status.get("status") == "not_found":
        try:
            params = TradingParameters(**(base_settings or {}))
        except Exception:
            params = TradingParameters()
        return not_in_session(data={
            "traders": [trader_id], "human_traders": [{"id": trader_id}],
            "game_params": {"predefined_goals": params.predefined_goals,
                           "num_human_traders": len(params.predefined_goals),
                           "trading_day_duration": params.trading_day_duration},
            "isWaitingForOthers": False
        })

    if session_status.get("status") == "waiting":
        return waiting(data={
            "traders": [trader_id], "human_traders": [{"id": trader_id}],
            "game_params": {"predefined_goals": [0], "num_human_traders": 1},
            "isWaitingForOthers": True
        })

    trader_manager = market_handler.get_trader_manager_by_trader_id(trader_id)
    if not trader_manager:
        raise HTTPException(status_code=404, detail="No market found for this trader")

    human_traders_data = [t.get_trader_params_as_dict() for t in trader_manager.human_traders]
    params_dict = trader_manager.params.model_dump()
    params_dict['num_human_traders'] = len(params_dict['predefined_goals'])

    return success(data={
        "traders": list(trader_manager.traders.keys()), "human_traders": human_traders_data,
        "game_params": params_dict, "isWaitingForOthers": False
    })


@router.get("/market_metrics")
async def get_market_metrics(trader_id: str, market_id: str, current_user: dict = Depends(get_current_user)):
    if trader_id != f"HUMAN_{current_user['gmail_username']}":
        raise HTTPException(status_code=403, detail="Unauthorized access to trader data")

    log_file_path = f"logs/{market_id}.log"
    try:
        processed_data = process_log_file(log_file_path)
        output = io.StringIO()
        write_to_csv(processed_data, output)
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=market_{market_id}_trader_{trader_id}_metrics.csv"}
        )
    except Exception:
        raise HTTPException(status_code=500, detail="Error processing market metrics")


@router.post("/trading/start")
async def start_trading_market(background_tasks: BackgroundTasks, request: Request):
    current_user = await get_current_user(request)
    gmail_username = current_user['gmail_username']
    trader_id = f"HUMAN_{gmail_username}"

    await market_handler.cleanup_finished_markets()

    session_status = market_handler.get_session_status_by_trader_id(trader_id)

    if session_status.get("status") == "not_found":
        params = TradingParameters(**(base_settings or {}))
        try:
            session_id, trader_id_assigned, role, goal = await market_handler.validate_and_assign_role(
                gmail_username, params
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to join session: {str(e)}")

    all_ready = await market_handler.mark_trader_ready_by_trader_id(trader_id)

    if all_ready:
        status_message = "Trading started successfully!"
        trader_manager = market_handler.get_trader_manager_by_trader_id(trader_id)
        if trader_manager:
            internal_session_id = market_handler.trader_to_market_lookup.get(trader_id)
            asyncio.create_task(trader_manager.launch())
            # Broadcast market_started via Socket.IO room
            from api.socketio_server import emit_to_market
            asyncio.create_task(
                emit_to_market(internal_session_id, "market_started", {"market_id": internal_session_id})
            )
    else:
        status_message = "Marked as ready. Waiting for other traders to be ready."

    internal_session_id = market_handler.trader_to_market_lookup.get(trader_id)
    ready_traders = list(market_handler.market_ready_traders.get(internal_session_id, set()))

    return success(ready_traders=ready_traders, all_ready=all_ready, message=status_message)



# Legacy WebSocket handler removed — replaced by Socket.IO events in api/socketio_server.py
