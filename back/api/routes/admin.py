"""Admin routes: /admin/* settings, treatments, generate-lab-links, reset, headless batch"""

import asyncio
from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Request, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

from core.data_models import TradingParameters
from core.trader_manager import TraderManager
from core.treatment_manager import treatment_manager
from ..auth import get_current_user, get_current_admin_user
from ..shared import base_settings, market_handler, accumulated_rewards
from utils.api_responses import success, not_found

router = APIRouter()


class BaseSettings(BaseModel):
    settings: dict


class TreatmentYAML(BaseModel):
    yaml_content: str


# --- Settings ---

@router.post("/admin/update_base_settings")
async def update_base_settings(settings: BaseSettings):
    from core.parameter_logger import ParameterLogger
    logger = ParameterLogger()

    base_settings.update(settings.settings)

    logger.log_parameter_state(current_state=base_settings, source='admin_update')

    if 'market_sizes' in settings.settings:
        try:
            market_sizes = settings.settings['market_sizes']
            if isinstance(market_sizes, str):
                market_sizes = [int(x.strip()) for x in market_sizes.split(',') if x.strip()]
            market_handler.session_manager.update_market_sizes(market_sizes)
            logger.log_parameter_state(
                current_state={'action': 'market_sizes_update', 'market_sizes': market_sizes},
                source='admin_update_market_sizes'
            )
        except Exception as e:
            print(f"Error updating market_sizes: {str(e)}")

    if 'predefined_goals' in settings.settings:
        try:
            updated_params = TradingParameters(**(base_settings or {}))
            market_handler.session_manager.update_session_pool_goals(updated_params)
            logger = ParameterLogger()
            logger.log_parameter_state(
                current_state={'action': 'goal_update', 'new_goals': settings.settings['predefined_goals']},
                source='admin_update_goals'
            )
            return success(message="Persistent settings updated and waiting sessions refreshed with new goals")
        except Exception as e:
            print(f"Error updating session pool goals: {str(e)}")
            return {"status": "partial_success", "message": f"Settings updated but failed to update waiting sessions: {str(e)}"}

    return success(message="Persistent settings updated")


@router.get("/admin/get_base_settings")
async def get_base_settings_endpoint():
    return success(data=base_settings)


@router.get("/admin/download_parameter_history")
async def download_parameter_history(current_user: dict = Depends(get_current_admin_user)):
    param_history_path = Path("logs/parameters/parameter_history.json")
    if not param_history_path.exists():
        return not_found("Parameter history file not found")
    return FileResponse(path=param_history_path, filename="parameter_history.json", media_type="application/json")


# --- Treatments ---

@router.post("/admin/update_treatments")
async def update_treatments(data: TreatmentYAML):
    try:
        count = treatment_manager.update_from_yaml(data.yaml_content)
        return success(message=f"Updated {count} treatments", treatments=treatment_manager.get_all_treatments())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/admin/get_treatments")
async def get_treatments():
    return success(yaml_content=treatment_manager.get_yaml_content(), treatments=treatment_manager.get_all_treatments())


@router.get("/admin/get_treatment_for_user/{username}")
async def get_treatment_for_user(username: str):
    market_count = len(market_handler.user_historical_markets.get(username, set()))
    treatment = treatment_manager.get_treatment_for_market(market_count)
    return success(
        username=username, markets_played=market_count,
        next_treatment_index=market_count, next_treatment=treatment
    )


@router.post("/admin/treatment-overrides")
async def set_treatment_overrides(request: Request, current_user: dict = Depends(get_current_admin_user)):
    try:
        body = await request.json()
        overrides = body.get("overrides", {})
        for cohort_id_str, params in overrides.items():
            cohort_id = int(cohort_id_str)
            market_handler.session_manager.cohort_treatment_overrides[cohort_id] = params
        return success(message="Treatment overrides updated", data={"overrides": overrides})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/treatment-overrides")
async def get_treatment_overrides(current_user: dict = Depends(get_current_admin_user)):
    return success(data={"overrides": market_handler.session_manager.cohort_treatment_overrides})


# --- Lab links ---

@router.post("/admin/generate-lab-links")
async def generate_lab_links(request: Request, current_user: dict = Depends(get_current_admin_user)):
    from ..lab_auth import generate_lab_tokens, lab_trader_map, LAB_TOKENS
    try:
        body = await request.json()
        count = body.get("count", 10)
        num_treatments = body.get("num_treatments", 1)
        treatment_overrides = body.get("treatment_overrides", None)

        LAB_TOKENS.clear()
        sm = market_handler.session_manager
        lab_usernames = [u for u in sm.user_historical_markets if u.startswith("LAB_")]
        for u in lab_usernames:
            sm.user_historical_markets.pop(u, None)
            sm.user_sessions.pop(u, None)
            sm.user_cohorts.pop(u, None)
            sm.user_ready_status.pop(u, None)
            sm.user_treatment_groups.pop(u, None)
            sm.permanent_speculators.discard(u)
            sm.permanent_informed_goals.pop(u, None)
        sm.cohort_members.clear()
        sm.cohort_sessions.clear()
        sm.cohort_treatment_overrides.clear()
        sm.cohort_persistent_session_ids.clear()
        lab_trader_map.clear()
        lab_trader_ids = [t for t in accumulated_rewards if t.startswith("HUMAN_LAB_")]
        for t in lab_trader_ids:
            del accumulated_rewards[t]

        origin = request.headers.get("origin", str(request.base_url).rstrip("/"))
        links = generate_lab_tokens(count, base_url=origin, num_treatments=num_treatments)

        sm.update_market_sizes([1] * count)

        if treatment_overrides and isinstance(treatment_overrides, dict):
            for cohort_id_str, overrides in treatment_overrides.items():
                cohort_id = int(cohort_id_str)
                sm.cohort_treatment_overrides[cohort_id] = overrides

        return success(message=f"Generated {count} lab links ({num_treatments} treatments)", data={"links": links})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate lab links: {str(e)}")


# --- Reset ---

@router.post("/admin/reset_state")
async def reset_state(current_user: dict = Depends(get_current_admin_user)):
    try:
        current_settings = base_settings.copy()
        await market_handler.reset_state()
        base_settings.update(current_settings)
        accumulated_rewards.clear()
        return success(message="Application state reset successfully")
    except Exception:
        raise HTTPException(status_code=500, detail="Error resetting application state")


@router.post("/test/reset_state")
async def test_reset_state():
    """Reset all application state INCLUDING historical markets - FOR TESTING ONLY"""
    try:
        current_settings = base_settings.copy()
        await market_handler.reset_state()
        market_handler.session_manager.user_historical_markets.clear()
        market_handler.session_manager.permanent_speculators.clear()
        market_handler.session_manager.permanent_informed_goals.clear()
        base_settings.update(current_settings)
        accumulated_rewards.clear()
        return success(message="Test reset completed (including historical markets)")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reset failed: {str(e)}")


# --- Headless batch ---

@router.post("/admin/run_headless_batch")
async def run_headless_batch(
    background_tasks: BackgroundTasks,
    num_markets: int = Query(default=3, ge=1, le=10),
    start_treatment: int = Query(default=0, ge=0),
    parallel: bool = Query(default=True),
    delay_seconds: int = Query(default=5, ge=1, le=60)
):
    import time as time_module
    import uuid

    session_id = f"SESSION_{int(time_module.time())}_{uuid.uuid4().hex[:8]}"

    async def run_single_market(market_index: int, treatment_idx: int):
        try:
            treatment = treatment_manager.get_treatment_for_market(treatment_idx)
            params_dict = dict(base_settings) if base_settings else {}
            if treatment:
                params_dict.update(treatment)
            params_dict["predefined_goals"] = []
            params = TradingParameters(**params_dict)
            market_id = f"{session_id}_MARKET_{market_index}"
            manager = TraderManager(params, market_id=market_id)
            market_handler.trader_managers[market_id] = manager
            print(f"Starting market {market_index} (treatment {treatment_idx}): {market_id}")
            await manager.launch()
            await manager.cleanup()
            print(f"Completed market {market_index}: {market_id}")
        except Exception as e:
            import traceback
            print(f"Market {market_index} (treatment {treatment_idx}) error: {e}")
            traceback.print_exc()

    async def run_batch():
        if parallel:
            tasks = [run_single_market(i, start_treatment + i) for i in range(num_markets)]
            await asyncio.gather(*tasks)
        else:
            for i in range(num_markets):
                await run_single_market(i, start_treatment + i)
                if i < num_markets - 1:
                    await asyncio.sleep(delay_seconds)

    background_tasks.add_task(run_batch)

    return success(
        session_id=session_id, num_markets=num_markets, start_treatment=start_treatment,
        parallel=parallel, message=f"Starting {num_markets} markets {'in parallel' if parallel else 'sequentially'} from treatment {start_treatment}"
    )


# --- Sessions monitoring ---

@router.get("/sessions")
async def list_sessions(current_user: dict = Depends(get_current_user)):
    await market_handler.cleanup_finished_markets()
    return market_handler.list_all_sessions()


@router.post("/sessions/{market_id}/force-start")
async def force_start_session(
    market_id: str,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    if market_id not in market_handler.trader_managers:
        raise HTTPException(status_code=404, detail="Market not found")

    manager = market_handler.trader_managers[market_id]
    market = manager.trading_market

    if market.trading_started:
        raise HTTPException(status_code=400, detail="Market session already started")

    if not market_handler.active_users.get(market_id):
        raise HTTPException(status_code=400, detail="Cannot start empty session")

    active_users = market_handler.active_users.get(market_id, set())
    for username in active_users:
        trader_id = f"HUMAN_{username}"
        await manager.trading_market.handle_register_me({
            "trader_id": trader_id, "trader_type": "human", "gmail_username": username
        })
        await market_handler.mark_trader_ready(trader_id, market_id)

    original_goals = manager.params.predefined_goals
    manager.params.predefined_goals = [100] * len(active_users)

    try:
        await manager.launch()
    finally:
        manager.params.predefined_goals = original_goals

    return success(message="Market session started successfully")


