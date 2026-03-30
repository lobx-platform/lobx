import asyncio
import io
from datetime import timedelta, datetime

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# main imports
from fastapi import (
    FastAPI, WebSocket, HTTPException, WebSocketDisconnect, 
    BackgroundTasks, Depends, Request, Response, Query
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse
from fastapi.security import HTTPBasic

# our stuff
from core.trader_manager import TraderManager
from core.simple_market_handler import SimpleMarketHandler
from core.data_models import TraderType, TradingParameters, UserRegistration, TraderRole
from .auth import get_current_user, get_current_admin_user, extract_gmail_username, is_user_registered, is_user_admin, custom_verify_id_token
from .prolific_auth import extract_prolific_params, validate_prolific_user, authenticate_prolific_user
from utils.calculate_metrics import process_log_file, write_to_csv
from utils.logfiles_analysis import order_book_contruction, calculate_trader_specific_metrics
from firebase_admin import auth
from utils.websocket_utils import sanitize_websocket_message
from utils.api_responses import success, error, not_found, waiting, not_in_session
from .random_picker import pick_random_element_new
from core.treatment_manager import treatment_manager

# python stuff we need
import json
import os
import csv
import zipfile
from pydantic import BaseModel, ValidationError
from pathlib import Path
from typing import Dict, Any, List, Optional
from .google_sheet_auth import get_registered_users

# init fastapi
app = FastAPI()
security = HTTPBasic()

# Global variables


# Initialize with default values from TradingParameters
# Use model_dump() to get a dictionary representation of all parameters
default_params = TradingParameters()
base_settings = default_params.model_dump()
accumulated_rewards = {}  # Store accumulated rewards per user

# CORS middleware for cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*", "Authorization"],
    expose_headers=["Content-Disposition"],
    max_age=3600,
)

# Separate middleware for security headers
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin-allow-popups"
    response.headers["Cross-Origin-Embedder-Policy"] = "require-corp"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    return response

market_handler = SimpleMarketHandler()
trader_managers = {}

# helper funcs
def get_historical_markets_count(username):
    return len(market_handler.user_historical_markets.get(username, set()))

def record_market_for_user(username, market_id):
    market_handler.user_historical_markets[username].add(market_id)

class BaseSettings(BaseModel):
    settings: dict

# Update the persistent settings endpoint
@app.post("/admin/update_base_settings")
async def update_base_settings(settings: BaseSettings):
    global base_settings  # Only use global when modifying

    # Import and set up parameter logger
    from core.parameter_logger import ParameterLogger
    logger = ParameterLogger()

    # Merge settings instead of replacing - this preserves fields not explicitly updated
    base_settings.update(settings.settings)

    # Log the complete current state
    logger.log_parameter_state(
        current_state=base_settings,
        source='admin_update'
    )

    # Update market_sizes if changed (for cohort system)
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

    # Update session pools with new goals if predefined_goals changed
    if 'predefined_goals' in settings.settings:
        try:
            # Create TradingParameters with updated settings
            updated_params = TradingParameters(**(base_settings or {}))

            # Update waiting session pools (clears permanent memory and updates goals)
            market_handler.session_manager.update_session_pool_goals(updated_params)

            logger = ParameterLogger()
            logger.log_parameter_state(
                current_state={'action': 'goal_update', 'new_goals': settings.settings['predefined_goals']},
                source='admin_update_goals'
            )

            return success(message="Persistent settings updated and waiting sessions refreshed with new goals")
        except Exception as e:
            print(f"Error updating session pool goals: {str(e)}")
            return {
                "status": "partial_success",
                "message": f"Settings updated but failed to update waiting sessions: {str(e)}"
            }

    return success(message="Persistent settings updated")

@app.get("/admin/get_base_settings")
async def get_base_settings():
    return success(data=base_settings)

@app.get("/admin/agentic_templates")
async def get_agentic_templates():
    """Get list of available agentic prompt templates."""
    from traders.agentic_trader import list_templates
    templates = list_templates()
    return success(templates=templates)


class AgenticPromptsYAML(BaseModel):
    yaml_content: str


@app.get("/admin/agentic_prompts_yaml")
async def get_agentic_prompts_yaml():
    """Get the full YAML content of agentic prompt templates."""
    from traders.agentic_trader import get_prompt_templates_yaml, list_templates
    return success(yaml_content=get_prompt_templates_yaml(), templates=list_templates())


@app.post("/admin/update_agentic_prompts")
async def update_agentic_prompts(data: AgenticPromptsYAML):
    """Update agentic prompt templates from YAML content."""
    from traders.agentic_trader import save_prompt_templates, list_templates
    try:
        count = save_prompt_templates(data.yaml_content)
        return success(message=f"Updated {count} agentic prompt templates", templates=list_templates())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/admin/agentic_template/{template_id}")
async def get_agentic_template(template_id: str):
    """Get a specific agentic prompt template as YAML."""
    from traders.agentic_trader import get_template_yaml
    try:
        yaml_content = get_template_yaml(template_id)
        return success(template_id=template_id, yaml_content=yaml_content)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/admin/agentic_template/{template_id}")
async def update_agentic_template(template_id: str, data: AgenticPromptsYAML):
    """Update a specific agentic prompt template from YAML content."""
    from traders.agentic_trader import save_template_yaml, list_templates
    try:
        save_template_yaml(template_id, data.yaml_content)
        return success(message=f"Updated template '{template_id}'", templates=list_templates())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/admin/download_parameter_history")
async def download_parameter_history(current_user: dict = Depends(get_current_admin_user)):
    """Download the parameter history JSON file"""
    param_history_path = Path("logs/parameters/parameter_history.json")
    if not param_history_path.exists():
        return not_found("Parameter history file not found")
    
    return FileResponse(
        path=param_history_path,
        filename="parameter_history.json",
        media_type="application/json"
    )


class TreatmentYAML(BaseModel):
    yaml_content: str


@app.post("/admin/update_treatments")
async def update_treatments(data: TreatmentYAML):
    try:
        count = treatment_manager.update_from_yaml(data.yaml_content)
        return success(message=f"Updated {count} treatments", treatments=treatment_manager.get_all_treatments())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/admin/get_treatments")
async def get_treatments():
    return success(yaml_content=treatment_manager.get_yaml_content(), treatments=treatment_manager.get_all_treatments())


@app.get("/admin/get_treatment_for_user/{username}")
async def get_treatment_for_user(username: str):
    market_count = len(market_handler.user_historical_markets.get(username, set()))
    treatment = treatment_manager.get_treatment_for_market(market_count)
    return success(
        username=username, markets_played=market_count,
        next_treatment_index=market_count, next_treatment=treatment
    )


async def verify_turnstile(token: str) -> bool:
    """Verify a Cloudflare Turnstile token server-side."""
    secret_key = os.environ.get('TURNSTILE_SECRET_KEY', '')
    if not secret_key:
        return True  # Skip verification if no secret key configured
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                'https://challenges.cloudflare.com/turnstile/v0/siteverify',
                data={'secret': secret_key, 'response': token},
            )
            return resp.json().get('success', False)
    except Exception as e:
        print(f"Turnstile verification error: {e}")
        return False

@app.post("/user/login")
async def user_login(request: Request):
    # Check for lab token first
    lab_token = request.query_params.get('LAB_TOKEN')
    if lab_token:
        from .lab_auth import validate_lab_token, lab_trader_map
        is_valid, lab_user = validate_lab_token(lab_token)
        if not is_valid:
            raise HTTPException(status_code=401, detail="Invalid or expired lab token")
        gmail_username = lab_user['gmail_username']
        trader_id = lab_user['trader_id']
        treatment_group = lab_user.get('treatment_group')
        lab_trader_map[trader_id] = lab_user
        await market_handler.remove_user_from_session(gmail_username)
        # Register forced cohort assignment if treatment_group is set
        if treatment_group is not None:
            market_handler.session_manager.user_treatment_groups[gmail_username] = treatment_group
        return success(
            message="Lab login successful",
            data={"trader_id": trader_id, "username": gmail_username, "is_admin": False,
                  "is_lab": True, "lab_token": lab_token, "treatment_group": treatment_group}
        )

    # Check for Prolific parameters
    prolific_params = await extract_prolific_params(request)
    if prolific_params:
        # Parse body once (both turnstile and authenticate_prolific_user need it)
        try:
            body = await request.json()
        except Exception:
            body = {}

        # Verify Turnstile token for Prolific users
        turnstile_token = body.get('turnstile_token')
        if turnstile_token:
            if not await verify_turnstile(turnstile_token):
                raise HTTPException(status_code=403, detail="Turnstile verification failed")

        # Validate Prolific credentials directly (avoid double request.json() call)
        username = body.get('username')
        password = body.get('password')
        is_valid, prolific_user = validate_prolific_user(prolific_params, username, password)
        if not is_valid:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        # Credentials already validated above
        gmail_username = prolific_user['gmail_username']
        trader_id = f"HUMAN_{gmail_username}"
        prolific_token = prolific_user.get('prolific_token', '')

        print(f"Authenticated Prolific user via params: {gmail_username}")

        # Remove user from any existing session (fresh start on login/refresh)
        await market_handler.remove_user_from_session(gmail_username)

        # DON'T assign session at login - wait until they click "Start Trading"
        return success(
            message="Prolific login successful",
            data={"trader_id": trader_id, "username": gmail_username, "is_admin": False,
                  "is_prolific": True, "prolific_token": prolific_token}
        )
    
    # If not Prolific, proceed with regular Firebase authentication
    auth_header = request.headers.get('Authorization')
    
    if not auth_header or not auth_header.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Invalid authentication method")
    
    token = auth_header.split('Bearer ')[1]
    decoded_token = custom_verify_id_token(token)
    email = decoded_token['email']
    gmail_username = extract_gmail_username(email)
    
    # Check registration
    form_id = TradingParameters().google_form_id
    if not is_user_registered(email, form_id):
        raise HTTPException(status_code=403, detail="User not registered in the study")
    
    trader_id = f"HUMAN_{gmail_username}"
    
    # Remove user from any existing session (fresh start on login/refresh)
    await market_handler.remove_user_from_session(gmail_username)
    
    # DON'T assign session at login - wait until they click "Start Trading"
    return success(message="Login successful", data={"username": email, "is_admin": is_user_admin(email), "trader_id": trader_id})

@app.post("/admin/login")
async def admin_login(request: Request):
    auth_header = request.headers.get('Authorization')
    
    if not auth_header or not auth_header.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Invalid authentication method")
    
    token = auth_header.split('Bearer ')[1]
    decoded_token = custom_verify_id_token(token)
    email = decoded_token['email']
    
    if not is_user_admin(email):
        raise HTTPException(status_code=403, detail="User does not have admin privileges")
    
    return success(message="Admin login successful", data={"username": email, "is_admin": True})


@app.get("/session/status")
async def get_session_status(request: Request, current_user: dict = Depends(get_current_user)):
    """
    Get the current session status for the authenticated user.
    Used by frontend to determine where to route the user after page refresh.
    """
    gmail_username = current_user['gmail_username']
    trader_id = f"HUMAN_{gmail_username}"
    is_admin = current_user.get('is_admin', False)
    is_prolific = current_user.get('is_prolific', False)
    
    # Get merged params for max markets info
    try:
        merged_params = TradingParameters(**(base_settings or {}))
    except Exception:
        merged_params = TradingParameters()
    
    # Check session status
    session_status = market_handler.get_session_status_by_trader_id(trader_id)
    
    # Get historical markets count
    historical_markets_count = get_historical_markets_count(gmail_username)
    max_markets = merged_params.max_markets_per_human
    
    # Determine the user's current status
    status = "authenticated"  # Default
    market_id = None
    onboarding_step = 0
    
    if session_status.get("status") == "active":
        status = "trading"
        # Get market ID if available
        trader_manager = market_handler.get_trader_manager_by_trader_id(trader_id)
        if trader_manager:
            market_id = trader_manager.market_id
    elif session_status.get("status") == "finished":
        # Market has ended - user should be on summary page
        status = "summary"
        market_id = session_status.get("market_id")
    elif session_status.get("status") == "waiting":
        status = "waiting"
    elif historical_markets_count >= max_markets and not is_admin:
        status = "complete"
    else:
        # Check if user has completed onboarding before (for Prolific users)
        if is_prolific:
            # Prolific users who have logged in before go to waiting
            status = "waiting"
            onboarding_step = 7  # Completed onboarding
        else:
            status = "onboarding"
    
    return success(data={
        "status": status, "trader_id": trader_id, "market_id": market_id,
        "onboarding_step": onboarding_step, "markets_completed": historical_markets_count,
        "max_markets": max_markets, "is_admin": is_admin, "is_prolific": is_prolific
    })


@app.post("/session/reset-for-new-market")
async def reset_session_for_new_market(request: Request, current_user: dict = Depends(get_current_user)):
    """
    Reset user's session to prepare for a new market.
    Called when user clicks "Continue to next market" from summary page.
    """
    gmail_username = current_user['gmail_username']

    # Remove user from any existing session
    await market_handler.remove_user_from_session(gmail_username)

    # Clean up any finished markets
    await market_handler.cleanup_finished_markets()

    return success(message="Session reset for new market", data={"username": gmail_username})


@app.get("/traders/defaults")
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

@app.post("/trading/initiate")
async def create_trading_market(background_tasks: BackgroundTasks, request: Request, current_user: dict = Depends(get_current_user)):
    # No need for global here since we're only reading
    try:
        merged_params = TradingParameters(**(base_settings or {}))
    except Exception as e:
        merged_params = TradingParameters()
        print(f"Error applying persistent settings: {str(e)}")
    
    # Get trader ID from the current user
    gmail_username = current_user['gmail_username']
    trader_id = f"HUMAN_{gmail_username}"
    
    # Log authentication info for debugging
    is_prolific = current_user.get('is_prolific', False)
    
    # Check session status using trader ID (simplified approach)
    session_status = market_handler.get_session_status_by_trader_id(trader_id)
    
    # If user is not in a session yet, return basic info so they can read instructions
    if session_status.get("status") == "not_found":
        return not_in_session(
            "User not in trading session yet",
            data={"trader_id": trader_id, "num_human_traders": len(merged_params.predefined_goals), "isWaitingForOthers": False}
        )

    # If user is in waiting session, return minimal waiting info (no session/market IDs)
    if session_status.get("status") == "waiting":
        return waiting(
            "Waiting for other traders to join",
            data={"trader_id": trader_id, "num_human_traders": len(merged_params.predefined_goals), "isWaitingForOthers": True}
        )
    
    # If market is active, get the trader manager using trader ID only
    trader_manager = market_handler.get_trader_manager_by_trader_id(trader_id)
    if not trader_manager:
        # This shouldn't happen if session status is active
        print(f"No trader manager found for {trader_id}")
        raise HTTPException(status_code=404, detail="No active market found for this user")
    
    # Update the manager's parameters with our merged params
    trader_manager.params = merged_params
    
    # Ensure the human trader has a record even if they don't trade
    # This is important for Prolific users who may not actively trade
    if hasattr(trader_manager, 'human_traders'):
        for human_trader in trader_manager.human_traders:
            if human_trader.id == trader_id and hasattr(human_trader, 'handle_TRADING_STARTED'):
                # This will trigger the zero-amount order for record-keeping
                print(f"Ensuring record for human trader: {trader_id}")
    
    return success(
        message="Trading market info retrieved",
        data={"trader_id": trader_id, "traders": list(trader_manager.traders.keys()),
              "human_traders": [t.id for t in trader_manager.human_traders],
              "num_human_traders": len(merged_params.predefined_goals), "isWaitingForOthers": False}
    )

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
        raise HTTPException(
            status_code=500, 
            detail=f"Error getting trader info: {str(e)}"
        )

@app.get("/trader_info/{trader_id}")
async def get_trader_info(trader_id: str):
    # Extract username from trader_id
    if not trader_id.startswith("HUMAN_"):
        raise HTTPException(status_code=404, detail="Invalid trader ID")
    
    username = trader_id[6:]  # Remove "HUMAN_" prefix
    
    # Check session status using trader ID (simplified approach)
    session_status = market_handler.get_session_status_by_trader_id(trader_id)
    
    # If user is not in a session yet, return basic default attributes so they can see page 8
    if session_status.get("status") == "not_found":
        # Get basic info for user not yet in session
        historical_markets_count = len(market_handler.user_historical_markets.get(username, set()))
        
        # Get parameters to determine initial allocations
        params = TradingParameters(**(base_settings or {}))
        
        # Create minimal trader data for not-yet-in-session state
        # DON'T send goal - let it be undefined until assigned
        trader_data = {
            'cash': params.initial_cash,
            'shares': params.initial_stocks,
            # 'goal': NOT INCLUDED - will be assigned when they join session
            'id': trader_id,
            'all_attributes': {
                'historical_markets_count': historical_markets_count,
                'is_admin': username in ['venvoooo', 'asancetta', 'marjonuzaj', 'fra160756', 'expecon', 'w.wu'],
                'params': base_settings,
                'isWaitingForOthers': False  # Not waiting yet - not in session
            }
        }
        
        return {
            "status": "not_in_session",
            "message": "Trader not in session yet - showing default attributes",
            "data": {
                **trader_data,
                "order_book_metrics": {},
                "trader_specific_metrics": {}
            }
        }
    
    # If user is in waiting session, return minimal trader info (no session/market IDs)
    if session_status.get("status") == "waiting":
        # Get basic info for session pool user
        historical_markets_count = len(market_handler.user_historical_markets.get(username, set()))
        
        # Get actual assigned values from session status
        assigned_cash = session_status.get("cash", 100000)
        assigned_shares = session_status.get("shares", 300)
        assigned_goal = session_status.get("goal", 0)
        
        # Create minimal trader data for waiting state
        trader_data = {
            'cash': assigned_cash,
            'shares': assigned_shares,
            'goal': assigned_goal,
            'id': trader_id,
            'all_attributes': {
                'historical_markets_count': historical_markets_count,
                'is_admin': username in ['venvoooo', 'asancetta', 'marjonuzaj', 'fra160756', 'expecon', 'w.wu'],
                'params': base_settings,  # Include current trading parameters
                'isWaitingForOthers': True
            }
        }
        
        return {
            "status": "waiting",
            "message": "Trader in session pool, waiting for market to start",
            "data": {
                **trader_data,
                "order_book_metrics": {},
                "trader_specific_metrics": {}
            }
        }
    
    # If market is active, get full trader info using trader ID only
    trader_manager = market_handler.get_trader_manager_by_trader_id(trader_id)

    # Use internal session/market ID for logging only (don't expose to frontend)
    internal_session_id = market_handler.trader_to_market_lookup.get(trader_id)

    if not trader_manager:
        # Market ended and trader_manager was cleaned up — compute metrics from log file
        if not internal_session_id:
            raise HTTPException(status_code=404, detail="Trader not found")

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
            # Check if log file exists before processing
            if os.path.exists(log_file_path):
                order_book_metrics = order_book_contruction(log_file_path)
                
                # Try both with and without quotes for trader ID lookup
                quoted_trader_id = f"'{trader_id}'"
                
                # First try with quotes (old format), then without quotes (new format)
                trader_specific_metrics = order_book_metrics.get(quoted_trader_id, {})
                if not trader_specific_metrics:
                    trader_specific_metrics = order_book_metrics.get(trader_id, {})
                
                # Exclude both quoted and unquoted trader IDs from general metrics
                trader_keys_to_exclude = {quoted_trader_id, trader_id}
                general_metrics = {k: v for k, v in order_book_metrics.items() if k not in trader_keys_to_exclude}

                if trader_specific_metrics:
                    trader_goal = trader_data.get('goal', 0)  # Get trader goal from trader data
                    trader_specific_metrics = calculate_trader_specific_metrics(
                        trader_specific_metrics, 
                        general_metrics, 
                        trader_goal
                    )
                    
                    # track rewards per market (avoid duplicates)
                    internal_session_id = market_handler.trader_to_market_lookup.get(trader_id)
                    if isinstance(trader_specific_metrics.get('Reward'), (int, float)):
                        if trader_id not in accumulated_rewards:
                            accumulated_rewards[trader_id] = {}
                        accumulated_rewards[trader_id][internal_session_id] = trader_specific_metrics['Reward']
                    
                    # select random reward from markets 2+ (skip first market)
                    all_rewards = list(accumulated_rewards.get(trader_id, {}).values())
                    if len(all_rewards) <= 1:
                        trader_specific_metrics['Accumulated_Reward'] = 0
                    else:
                        trader_specific_metrics['Accumulated_Reward'] = pick_random_element_new(all_rewards[1:])
                else:
                    # User was in the market but didn't trade — show zeros, not N/A
                    trader_specific_metrics = {
                        'Trades': 0,
                        'Num_Buy': 0,
                        'Num_Sell': 0,
                        'Remaining_Trades': 0,
                        'PnL': 0,
                        'Reward': 0,
                        'Accumulated_Reward': 0,
                    }
            else:
                print(f"Log file not found: {log_file_path}")
                order_book_metrics = {}
                trader_specific_metrics = {}

        except Exception as e:
            print(f"Error processing metrics for trader {trader_id}: {str(e)}")
            print(f"Log file path: {log_file_path}")
            order_book_metrics = {}
            trader_specific_metrics = {}

        # Add flag to indicate not waiting
        if 'all_attributes' not in trader_data:
            trader_data['all_attributes'] = {}
        trader_data['all_attributes']['isWaitingForOthers'] = False

        return success(message="Trader found", data={**trader_data, "order_book_metrics": order_book_metrics, "trader_specific_metrics": trader_specific_metrics})

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting trader info: {str(e)}")

@app.get("/trader/{trader_id}/market")
async def get_trader_market(trader_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    # Log authentication info for debugging
    is_prolific = current_user.get('is_prolific', False)
    gmail_username = current_user.get('gmail_username', '')
    
    # Verify that the current user has access to this trader_id
    # For Prolific users, we need to ensure they can only access their own trader
    if is_prolific and f"HUMAN_{gmail_username}" != trader_id:
        print(f"Prolific user {gmail_username} attempted to access trader {trader_id}")
        raise HTTPException(status_code=403, detail="You can only access your own trader data")
    
    # Check session status using trader ID (simplified approach)
    session_status = market_handler.get_session_status_by_trader_id(trader_id)
    
    # If user is not in a session yet (reading instructions), return minimal default info
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

    # If user is in waiting session, return minimal session info (no session/market IDs)
    if session_status.get("status") == "waiting":
        return waiting(data={
            "traders": [trader_id], "human_traders": [{"id": trader_id}],
            "game_params": {"predefined_goals": [0], "num_human_traders": 1},
            "isWaitingForOthers": True
        })
    
    # If market is active, get the trader manager using trader ID only
    trader_manager = market_handler.get_trader_manager_by_trader_id(trader_id)
    if not trader_manager:
        # This shouldn't happen if session status is active
        print(f"No trader manager found for {trader_id}")
        raise HTTPException(status_code=404, detail="No market found for this trader")

    human_traders_data = [t.get_trader_params_as_dict() for t in trader_manager.human_traders]
    params_dict = trader_manager.params.model_dump()
    
    # Add expected traders count based on predefined goals
    params_dict['num_human_traders'] = len(params_dict['predefined_goals'])
    
    # Ensure the human trader has a record even if they don't trade
    # This is important for Prolific users who may not actively trade
    if trader_id.startswith("HUMAN_"):
        for human_trader in trader_manager.human_traders:
            if human_trader.id == trader_id and hasattr(human_trader, 'handle_TRADING_STARTED'):
                # This will ensure the trader has a record in the system
                print(f"Ensuring record for human trader: {trader_id} in market endpoint")

    return success(data={
        "traders": list(trader_manager.traders.keys()), "human_traders": human_traders_data,
        "game_params": params_dict, "isWaitingForOthers": False
    })



async def send_to_frontend(websocket: WebSocket, trader_manager):
    while True:
        trading_market = trader_manager.trading_market
        time_update = {
            "type": "time_update",
            "data": {
                "current_time": trading_market.current_time.isoformat(),
                "is_trading_started": trading_market.trading_started,
                "remaining_time": max(0, (
                    trading_market.start_time
                    + timedelta(minutes=trading_market.duration)
                    - trading_market.current_time
                ).total_seconds())
                if trading_market.trading_started
                else None,
                "current_human_traders": len(trader_manager.human_traders),
                "expected_human_traders": len(trader_manager.params.predefined_goals),
            },
        }
        try:
            sanitized_update = sanitize_websocket_message(time_update)
            await websocket.send_json(sanitized_update)
        except Exception as e:
            print(f"Error sending time update: {e}")
        await asyncio.sleep(1)

async def receive_from_frontend(websocket: WebSocket, trader):
    while True:
        try:
            message = await asyncio.wait_for(websocket.receive_text(), timeout=0.1)
            parsed_message = json.loads(message)
            
            if parsed_message.get('type') == 'order':
                async with trader_locks[trader.id]:
                    await trader.on_message_from_client(message)
            else:
                await trader.on_message_from_client(message)
                
        except (asyncio.TimeoutError, WebSocketDisconnect, json.JSONDecodeError):
            continue
        except Exception:
            return

@app.get("/market_metrics")
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

@app.websocket("/trader/{trader_id}")
async def websocket_trader_endpoint(websocket: WebSocket, trader_id: str):
    await websocket.accept()
    internal_session_id = None
    gmail_username = None
    
    try:
        token = await websocket.receive_text()
        
        # Check if this is a Lab token
        is_lab = False
        if token.startswith('lab_'):
            from .lab_auth import validate_lab_token, lab_trader_map
            is_valid, lab_user = validate_lab_token(token)
            if is_valid:
                gmail_username = lab_user['gmail_username']
                is_lab = True
                lab_trader_map[lab_user['trader_id']] = lab_user
                print(f"Authenticated Lab user via WebSocket: {gmail_username}")
            elif trader_id.startswith('HUMAN_'):
                gmail_username = trader_id[6:]
                is_lab = True
                print(f"Lab token not found but using trader_id: {gmail_username}")

        # Check if this is a Prolific token
        is_prolific = False
        if not is_lab and (token.startswith('prolific_') or token == 'no-auth'):
            # Extract username from trader_id for Prolific users
            # Format is typically HUMAN_123456abcdef
            if trader_id.startswith('HUMAN_'):
                gmail_username = trader_id[6:]  # Remove 'HUMAN_' prefix
                is_prolific = True
                print(f"Authenticated Prolific user via WebSocket: {gmail_username}")
        elif not is_lab and not is_prolific:
            # Regular Firebase authentication
            try:
                decoded_token = custom_verify_id_token(token)
                email = decoded_token['email']
                gmail_username = extract_gmail_username(email)
            except Exception as e:
                print(f"WebSocket token verification failed: {str(e)}")
                await websocket.close(code=1008, reason="Authentication failed")
                return
        
        if not gmail_username:
            await websocket.close(code=1008, reason="Invalid authentication")
            return
        
        # Check session status using trader ID (simplified approach)
        session_status = market_handler.get_session_status_by_trader_id(trader_id)
        
        if session_status.get("status") == "not_found":
            print(f"Trader {trader_id} not in any session")
            await websocket.close(code=1008, reason="Not in any session")
            return
        
        # If user is in waiting session, keep connection open to notify when market starts
        if session_status.get("status") == "waiting":
            # Store WebSocket for this waiting trader
            session_id = session_status.get("session_id")
            
            # Send initial waiting status
            waiting_message = {
                "type": "session_waiting",
                "data": {
                    "status": "waiting",
                    "message": "Waiting for other traders to join",
                    "isWaitingForOthers": True
                }
            }
            sanitized_waiting = sanitize_websocket_message(waiting_message)
            await websocket.send_json(sanitized_waiting)
            
            # Keep connection open and wait for market to start
            try:
                while True:
                    # Check if session has been converted to active market
                    new_status = market_handler.get_session_status_by_trader_id(trader_id)
                    
                    if new_status.get("status") == "active":
                        # Market started! Notify trader
                        market_started_message = {
                            "type": "market_started",
                            "data": {
                                "status": "active",
                                "message": "Market is now active!",
                                "trading_started": True
                            }
                        }
                        sanitized_started = sanitize_websocket_message(market_started_message)
                        await websocket.send_json(sanitized_started)
                        await websocket.close(code=1000, reason="Market started")
                        return
                    
                    # Wait a bit before checking again
                    await asyncio.sleep(1)
                    
            except WebSocketDisconnect:
                print(f"Trader {trader_id} disconnected from waiting room")
                return
            except Exception as e:
                print(f"Error in waiting room WebSocket for {trader_id}: {str(e)}")
                return
        
        # If market is active, get the trader manager using trader ID only
        trader_manager = market_handler.get_trader_manager_by_trader_id(trader_id)
        if not trader_manager:
            print(f"No trader manager found for {trader_id} in active market")
            await websocket.close(code=1008, reason="No trader manager found")
            return
            
        # Get internal session/market ID for logging only (don't expose to frontend)
        internal_session_id = market_handler.trader_to_market_lookup.get(trader_id)
        trader = trader_manager.get_trader(trader_id)
        if not trader:
            print(f"No trader found for {trader_id}")
            await websocket.close(code=1008, reason="Trader not found")
            return
        
        market_handler.add_user_to_market(gmail_username, internal_session_id)
        
        initial_count = {
            "type": "trader_count_update",
            "data": {
                "current_human_traders": len(market_handler.active_users.get(internal_session_id, set())),
                "expected_human_traders": len(trader_manager.params.predefined_goals),
                "market_id": internal_session_id
            }
        }
        sanitized_count = sanitize_websocket_message(initial_count)
        await websocket.send_json(sanitized_count)
        
        await trader.connect_to_socket(websocket)
        
        send_task = asyncio.create_task(send_to_frontend(websocket, trader_manager))
        receive_task = asyncio.create_task(receive_from_frontend(websocket, trader))
        
        done, pending = await asyncio.wait(
            [send_task, receive_task],
            return_when=asyncio.FIRST_COMPLETED
        )
        
        for task in pending:
            task.cancel()
            
    except WebSocketDisconnect:
        # Record market if it was active when disconnected
        if internal_session_id and gmail_username and trader_manager and trader_manager.trading_market.trading_started:
            if gmail_username not in market_handler.user_historical_markets:
                market_handler.user_historical_markets[gmail_username] = set()
            market_handler.user_historical_markets[gmail_username].add(internal_session_id)
    except Exception:
        pass
    finally:
        if internal_session_id and gmail_username:
            market_handler.remove_user_from_market(gmail_username, internal_session_id)
            await broadcast_trader_count(internal_session_id)
        try:
            await websocket.close()
        except RuntimeError:
            # Ignore "websocket.close" after response completed error
            pass

current_dir = Path(__file__).resolve().parent
ROOT_DIR = current_dir.parent / "logs"

@app.get("/files")
async def list_files(
    path: str = Query("", description="Relative path to browse")
):
    try:
        full_path = (ROOT_DIR / path).resolve()
        
        if not full_path.is_relative_to(ROOT_DIR):
            raise HTTPException(status_code=403, detail="Access denied")
        
        if not full_path.exists():
            raise HTTPException(status_code=404, detail="Path not found")
        
        if full_path.is_file():
            return {"type": "file", "name": full_path.name}
        
        files = []
        directories = []
        
        for item in full_path.iterdir():
            # Get last modified time
            mod_time = datetime.fromtimestamp(item.stat().st_mtime)
            
            if item.is_file():
                files.append({
                    "type": "file", 
                    "name": item.name,
                    "modified": mod_time
                })
            elif item.is_dir():
                directories.append({
                    "type": "directory", 
                    "name": item.name,
                    "modified": mod_time
                })
        
        # Sort files and directories by modification time (newest first)
        files.sort(key=lambda x: x["modified"], reverse=True)
        directories.sort(key=lambda x: x["modified"], reverse=True)
        
        # Remove the modification time from the response
        files = [{"type": f["type"], "name": f["name"]} for f in files]
        directories = [{"type": d["type"], "name": d["name"]} for d in directories]
        
        return {
            "current_path": str(full_path.relative_to(ROOT_DIR)),
            "parent_path": str(full_path.parent.relative_to(ROOT_DIR)) if full_path != ROOT_DIR else None,
            "directories": directories,
            "files": files
        }
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")

import re

@app.get("/files/grouped")
async def list_files_grouped():
    """Returns log files grouped by session for heatmap display."""
    try:
        multi_market_pattern = re.compile(r'^(?:COHORT\d+_)?SESSION_(\d+_[a-f0-9]+)_MARKET_(\d+)\.log$', re.IGNORECASE)
        single_market_pattern = re.compile(r'^(?:COHORT\d+_)?SESSION_(\d+_[a-f0-9]+)_trading\.log$', re.IGNORECASE)
        cohort_market_pattern = re.compile(r'^COHORT\d+_SESSION_(\d+_[a-f0-9]+)_trading_market(\d+)\.log$', re.IGNORECASE)
        
        sessions = {}
        ungrouped = []
        max_market = 0
        
        for item in ROOT_DIR.iterdir():
            if not item.is_file() or not item.name.endswith('.log'):
                continue
            filename = item.name
            session_id = None
            market_num = None
            match = multi_market_pattern.match(filename)
            if match:
                session_id = match.group(1)
                market_num = int(match.group(2))
            else:
                match = cohort_market_pattern.match(filename)
                if match:
                    session_id = match.group(1)
                    market_num = int(match.group(2))
                else:
                    match = single_market_pattern.match(filename)
                    if match:
                        session_id = match.group(1)
                        market_num = 1
            if session_id is not None:
                max_market = max(max_market, market_num)
                if session_id not in sessions:
                    sessions[session_id] = {'markets': {}}
                sessions[session_id]['markets'][market_num] = filename
            else:
                ungrouped.append(filename)
        
        session_list = []
        for session_id, data in sorted(sessions.items(), key=lambda x: x[0], reverse=True):
            session_list.append({'session_id': session_id, 'markets': data['markets']})
        
        return {'sessions': session_list, 'max_market': max_market, 'ungrouped': ungrouped}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/files/{file_path:path}")
async def get_file(file_path: str):
    try:
        full_path = (ROOT_DIR / file_path).resolve()
        
        if not full_path.is_relative_to(ROOT_DIR):
            raise HTTPException(status_code=403, detail="Access denied")
        
        if not full_path.is_file():
            raise HTTPException(status_code=404, detail="File not found")
        
        return FileResponse(full_path)
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")


# lets start trading!
@app.post("/trading/start")
async def start_trading_market(background_tasks: BackgroundTasks, request: Request):
    # Special handling for Prolific users
    prolific_params = await extract_prolific_params(request)
    if prolific_params:
        # Use the new authenticate_prolific_user function instead of validate_prolific_user directly
        try:
            prolific_user = await authenticate_prolific_user(request)
            if prolific_user:
                current_user = prolific_user
                print(f"Authenticated Prolific user via params in /trading/start: {prolific_user['gmail_username']}")
            else:
                # Fall back to regular authentication if prolific authentication fails
                current_user = await get_current_user(request)
        except HTTPException as e:
            print(f"Prolific authentication failed: {str(e)}")
            # Fall back to regular authentication
            current_user = await get_current_user(request)
    else:
        # Regular authentication for non-Prolific users
        current_user = await get_current_user(request)
    # Log authentication info for debugging
    is_prolific = current_user.get('is_prolific', False)
    gmail_username = current_user['gmail_username']
    trader_id = f"HUMAN_{gmail_username}"
    
    # Clean up any finished markets first (so users can join new markets)
    await market_handler.cleanup_finished_markets()
    
    # Check session status using trader ID (simplified approach)
    session_status = market_handler.get_session_status_by_trader_id(trader_id)
    
    # If user is not in a session yet, this is when they join!
    if session_status.get("status") == "not_found":
        params = TradingParameters(**(base_settings or {}))
        
        try:
            # Join session and get role/goal assignment
            session_id, trader_id_assigned, role, goal = await market_handler.validate_and_assign_role(
                gmail_username, 
                params
            )
        except Exception as e:
            print(f"[ERROR] Failed to assign user to session: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to join session: {str(e)}")
    
    # Mark trader ready and start trading if possible using trader ID only
    all_ready = await market_handler.mark_trader_ready_by_trader_id(trader_id)
    print(f"[DEBUG] trading/start: trader_id={trader_id}, all_ready={all_ready}")

    if all_ready:
        status_message = "Trading started successfully!"
        
        # Get the trader manager to start trading session
        trader_manager = market_handler.get_trader_manager_by_trader_id(trader_id)
        if trader_manager:
            # Get internal session/market ID for background tasks only (don't expose to frontend)
            internal_session_id = market_handler.trader_to_market_lookup.get(trader_id)
            
            # Actually launch the trading session - this was missing!
            background_tasks.add_task(trader_manager.launch)
            background_tasks.add_task(broadcast_trader_count, internal_session_id)
    else:
        status_message = "Marked as ready. Waiting for other traders to be ready."
    
    # Get internal session/market ID for ready traders info only (don't expose to frontend)
    internal_session_id = market_handler.trader_to_market_lookup.get(trader_id)
    ready_traders = list(market_handler.market_ready_traders.get(internal_session_id, set()))
    
    return success(ready_traders=ready_traders, all_ready=all_ready, message=status_message)

# ============================================================================
# TESTING API - REST endpoints for easy external testing without WebSocket
# ============================================================================

@app.post("/api/test/place_order")
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


@app.post("/api/test/cancel_order")
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


@app.get("/api/test/session_info/{trader_id}")
async def test_get_session_info(trader_id: str):
    """Get session info for a trader (used to find log files)"""
    session_id = market_handler.trader_to_market_lookup.get(trader_id)
    if not session_id:
        raise HTTPException(404, "Trader not in active session")

    return success(data={"session_id": session_id, "trader_id": trader_id, "log_file": f"logs/{session_id}.log"})


@app.get("/api/test/trader_inventory/{trader_id}")
async def test_get_trader_inventory(trader_id: str):
    """Get detailed inventory info for a trader - for debugging inventory constraint issues"""
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


@app.post("/api/test/verify_inventory_constraint")
async def test_verify_inventory_constraint(request: Request):
    """
    Test endpoint to verify inventory constraint is working.
    Attempts to place a SELL order for more shares than available.
    Body: {trader_id, price, amount (optional, defaults to shares+1 to trigger constraint)}
    Should return success=false if constraint is working.
    """
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

    # Get current inventory state
    current_shares = trader.shares
    available_shares = trader.get_available_shares()

    # Amount to sell: either specified or more than available to test constraint
    amount = data.get("amount", available_shares + 1)

    # Try to place a sell order (ASK = -1, BID = 1)
    from core.data_models import OrderType
    order_id = await trader.post_new_order(amount, price, OrderType.ASK)  # ASK = -1 = SELL

    return success(test_result={
        "order_accepted": order_id is not None, "order_id": order_id,
        "constraint_working": order_id is None,
        "shares_before": current_shares, "available_shares": available_shares,
        "attempted_sell_amount": amount,
        "message": "Inventory constraint is WORKING correctly" if order_id is None else "WARNING: Order was accepted despite insufficient shares!"
    })


@app.post("/api/test/create_test_session")
async def create_test_session(request: Request):
    """
    Create a standalone test session with a mock human trader for inventory testing.
    No authentication required.
    Body: {initial_shares (default 10), initial_cash (default 10000)}
    Returns the trader_id that can be used with other test endpoints.
    """
    data = await request.json() if request.headers.get("content-type") == "application/json" else {}
    initial_shares = data.get("initial_shares", 10)
    initial_cash = data.get("initial_cash", 10000)

    import time as time_module
    import uuid

    # Create unique test session
    test_session_id = f"TEST_SESSION_{int(time_module.time())}_{uuid.uuid4().hex[:8]}"
    test_username = f"test_user_{uuid.uuid4().hex[:8]}"
    trader_id = f"HUMAN_{test_username}"

    # Create params with the test configuration
    params_dict = dict(base_settings) if base_settings else {}
    params_dict["initial_stocks"] = initial_shares
    params_dict["initial_cash"] = initial_cash
    params_dict["trading_day_duration"] = 5.0  # 5 minutes for testing
    params_dict["num_noise_traders"] = 1  # minimal noise traders
    params_dict["num_informed_traders"] = 0
    params_dict["num_agentic_traders"] = 0
    params_dict["predefined_goals"] = [0]  # speculator role
    params_dict["market_sizes"] = [1]  # single trader market

    params = TradingParameters(**params_dict)

    # Create trader manager
    manager = TraderManager(params, market_id=test_session_id)
    market_handler.trader_managers[test_session_id] = manager

    # Add human trader manually
    from core.data_models import TraderRole
    await manager.add_human_trader(test_username, TraderRole.SPECULATOR, goal=0)

    # Register trader in ALL lookups (this was the missing piece)
    market_handler.trader_to_market_lookup[trader_id] = test_session_id
    market_handler.active_users[test_session_id] = {test_username}
    market_handler.market_ready_traders[test_session_id] = {trader_id}

    # Also register in session_manager so get_trader_manager works
    market_handler.session_manager.user_sessions[test_username] = test_session_id
    market_handler.session_manager.active_markets[test_session_id] = manager

    # Initialize and start trading
    await manager.trading_market.initialize()
    manager.trading_market.trading_started = True
    await manager.trading_market.start_trading()

    # Get trader info
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


# Market monitoring endpoint
@app.get("/sessions")
async def list_sessions(current_user: dict = Depends(get_current_user)):
    """List only pending and active market sessions for monitoring"""
    # Clean up any finished markets first
    await market_handler.cleanup_finished_markets()
    
    # Use the elegant new session listing
    return market_handler.list_all_sessions()

@app.post("/sessions/{market_id}/force-start")
async def force_start_session(
    market_id: str,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """Force start a trading session even if it's not full"""
    if market_id not in market_handler.trader_managers:
        raise HTTPException(status_code=404, detail="Market not found")
        
    manager = market_handler.trader_managers[market_id]
    market = manager.trading_market
    
    if market.trading_started:
        raise HTTPException(status_code=400, detail="Market session already started")
        
    if not market_handler.active_users.get(market_id):
        raise HTTPException(status_code=400, detail="Cannot start empty session")
    
    # Register all active users first
    active_users = market_handler.active_users.get(market_id, set())
    for username in active_users:
        trader_id = f"HUMAN_{username}"
        await manager.trading_market.handle_register_me({
            "trader_id": trader_id,
            "trader_type": "human",
            "gmail_username": username
        })
        # Mark each human trader as ready
        await market_handler.mark_trader_ready(trader_id, market_id)
    
    # Temporarily store the original predefined_goals
    original_goals = manager.params.predefined_goals
    
    # Modify predefined_goals to match current number of users
    manager.params.predefined_goals = [100] * len(active_users)
    
    try:
        # Launch using the normal initialization process
        await manager.launch()
    finally:
        # Restore original predefined_goals
        manager.params.predefined_goals = original_goals
    
    return success(message="Market session started successfully")





# keep our user list fresh
async def periodic_update_registered_users():
    while True:
        try:
            form_id = TradingParameters().google_form_id
            get_registered_users(force_update=True, form_id=form_id)
        except Exception:
            pass
        finally:
            await asyncio.sleep(300)  # 5 min sleep

# time offset calc loop
async def periodic_time_offset_calculation():
    while True:
        await asyncio.sleep(3600)  # 1 hour sleep

# startup tasks
@app.on_event("startup")
async def startup_event():
    # Log default parameters at startup
    from core.parameter_logger import ParameterLogger
    logger = ParameterLogger()
    logger.log_parameter_state(
        current_state=base_settings,
        source='system_startup'
    )
    
    # Start background tasks
    asyncio.create_task(periodic_update_registered_users())
    asyncio.create_task(periodic_time_offset_calculation())

# quick market check
def is_market_valid(market_id: str) -> bool:
    """Check if market is active"""
    if market_id not in trader_managers:
        return False
    
    trader_manager = trader_managers[market_id]
    return trader_manager.trading_market.active

# nuke everything from orbit
@app.post("/admin/reset_state")
async def reset_state(current_user: dict = Depends(get_current_admin_user)):
    """Reset all application state except settings"""
    try:
        global base_settings, accumulated_rewards
        current_settings = base_settings.copy()
        await market_handler.reset_state()
        base_settings = current_settings
        accumulated_rewards = {}  # Reset accumulated rewards
        
        # Preserve historical markets by not clearing market_handler.user_historical_markets
        return success(message="Application state reset successfully")
        
    except Exception:
        raise HTTPException(
            status_code=500, 
            detail="Error resetting application state"
        )

# Test-only reset endpoint (no auth required) - for automated testing
@app.post("/test/reset_state")
async def test_reset_state():
    """Reset all application state INCLUDING historical markets - FOR TESTING ONLY"""
    try:
        global base_settings, accumulated_rewards
        current_settings = base_settings.copy()
        await market_handler.reset_state()
        # Also clear historical markets for clean test runs
        market_handler.session_manager.user_historical_markets.clear()
        market_handler.session_manager.permanent_speculators.clear()
        market_handler.session_manager.permanent_informed_goals.clear()
        base_settings = current_settings
        accumulated_rewards = {}
        
        return success(message="Test reset completed (including historical markets)")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reset failed: {str(e)}")


# headless experiment runner - run markets with only AI traders
@app.post("/admin/run_headless_batch")
async def run_headless_batch(
    background_tasks: BackgroundTasks,
    num_markets: int = Query(default=3, ge=1, le=10),
    start_treatment: int = Query(default=0, ge=0),
    parallel: bool = Query(default=True, description="Run markets simultaneously (True) or sequentially (False)"),
    delay_seconds: int = Query(default=5, ge=1, le=60, description="Delay between sequential markets (ignored if parallel=True)")
):
    """
    Run multiple headless markets as a session.
    
    - num_markets: how many markets to run in this session
    - start_treatment: which treatment index to start from
    - parallel: if True, all markets run simultaneously; if False, run sequentially
    - delay_seconds: pause between sequential markets (ignored if parallel)
    """
    import time as time_module
    import uuid
    
    # Use consistent SESSION naming format
    session_id = f"SESSION_{int(time_module.time())}_{uuid.uuid4().hex[:8]}"
    
    async def run_single_market(market_index: int, treatment_idx: int):
        """Run a single market."""
        try:
            treatment = treatment_manager.get_treatment_for_market(treatment_idx)
            params_dict = dict(base_settings) if base_settings else {}
            if treatment:
                params_dict.update(treatment)
            
            params_dict["predefined_goals"] = []
            
            if params_dict.get("num_agentic_traders", 0) == 0:
                params_dict["num_agentic_traders"] = 1
                params_dict["agentic_prompt_template"] = "buyer_20_default"
            
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
            # run all markets simultaneously
            tasks = [
                run_single_market(i, start_treatment + i)
                for i in range(num_markets)
            ]
            await asyncio.gather(*tasks)
        else:
            # run markets sequentially
            for i in range(num_markets):
                await run_single_market(i, start_treatment + i)
                if i < num_markets - 1:
                    await asyncio.sleep(delay_seconds)
    
    background_tasks.add_task(run_batch)
    
    return success(
        session_id=session_id, num_markets=num_markets, start_treatment=start_treatment,
        parallel=parallel, message=f"Starting {num_markets} markets {'in parallel' if parallel else 'sequentially'} from treatment {start_treatment}"
    )

        
# headcount!
async def broadcast_trader_count(market_id: str):
    """Broadcast current trader count to all traders"""
    trader_manager = market_handler.trader_managers.get(market_id)
    if not trader_manager:
        return
        
    current_traders = len(market_handler.active_users[market_id])
    expected_traders = len(trader_manager.params.predefined_goals)
    
    count_message = {
        "type": "trader_count_update",
        "data": {
            "current_human_traders": current_traders,
            "expected_human_traders": expected_traders,
            "market_id": market_id
        }
    }
    
    # spread the word
    for trader in trader_manager.human_traders:
        if hasattr(trader, 'websocket') and trader.websocket:
            try:
                sanitized_count_message = sanitize_websocket_message(count_message)
                await trader.websocket.send_json(sanitized_count_message)
            except Exception:
                pass


# Prolific settings model
class ProlificSettings(BaseModel):
    settings: Dict[str, str]

# Questionnaire response model
class QuestionnaireResponse(BaseModel):
    trader_id: str
    responses: List[str]
    market_number: Optional[int] = None

# Pre-market interaction model
class PremarketInteraction(BaseModel):
    trader_id: str
    question_index: int
    question_text: str
    selected_answer: str
    is_correct: bool

# Consent form data model
class ConsentData(BaseModel):
    trader_id: str = ''  # Make trader_id optional
    user_id: str = ''
    user_type: str = ''  # 'google' or 'prolific'
    prolific_id: str = ''
    consent_given: bool = True
    consent_timestamp: str = ''

# Debug endpoint for consent
@app.post("/consent/debug")
async def debug_consent(data: dict):
    print("\n\n==== CONSENT DEBUG CALLED =====")
    print(f"Received raw data: {data}")
    
    try:
        # Just echo back the data
        return success(received=data)
    except Exception as e:
        print(f"ERROR in debug endpoint: {str(e)}")
        return {"status": "error", "message": str(e)}

# Get Prolific settings from .env file and in-memory storage
@app.get("/admin/prolific-settings")
async def get_prolific_settings(current_user: dict = Depends(get_current_admin_user)):
    # Import the in-memory credentials storage
    from api.prolific_auth import IN_MEMORY_CREDENTIALS
    try:
        env_path = Path(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))) / ".env"
        
        if not env_path.exists():
            return {
                "status": "error",
                "message": ".env file not found"
            }
        
        # Read the .env file
        env_content = env_path.read_text()
        
        # Extract Prolific settings
        prolific_settings = {}
        
        # First check for credentials in memory
        if IN_MEMORY_CREDENTIALS:
            # Convert in-memory credentials to string format (newline-separated for frontend)
            creds_str = "\n".join([f"{username},{password}" for username, password in IN_MEMORY_CREDENTIALS.items()])
            prolific_settings["PROLIFIC_CREDENTIALS"] = creds_str
            print(f"Returning {len(IN_MEMORY_CREDENTIALS)} credential pairs from memory")
        
        # Extract other settings from .env file
        for line in env_content.splitlines():
            if line.startswith("PROLIFIC_STUDY_ID="):
                prolific_settings["PROLIFIC_STUDY_ID"] = line.split("=", 1)[1]
            elif line.startswith("PROLIFIC_REDIRECT_URL="):
                prolific_settings["PROLIFIC_REDIRECT_URL"] = line.split("=", 1)[1]
            elif line.startswith("PROLIFIC_CREDENTIALS=") and "PROLIFIC_CREDENTIALS" not in prolific_settings:
                # Only use .env credentials if no in-memory credentials exist
                # Convert space-separated to newline-separated for frontend display
                creds = line.split("=", 1)[1]
                prolific_settings["PROLIFIC_CREDENTIALS"] = creds.replace(" ", "\n")
        
        return success(data=prolific_settings)
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

# --- Per-trader JSON questionnaire helpers ---
_trader_locks: Dict[str, asyncio.Lock] = {}

def _get_questionnaire_dir():
    d = ROOT_DIR / "questionnaire"
    d.mkdir(exist_ok=True)
    return d

def _get_trader_json_path(trader_id: str) -> Path:
    return _get_questionnaire_dir() / f"{trader_id}.json"

def _read_trader_data(trader_id: str) -> dict:
    path = _get_trader_json_path(trader_id)
    if path.exists():
        with open(path, 'r') as f:
            return json.load(f)
    return {"trader_id": trader_id, "premarket_interactions": [], "postmarket_responses": None}

def _write_trader_data(trader_id: str, data: dict):
    path = _get_trader_json_path(trader_id)
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)

async def _get_lock(trader_id: str) -> asyncio.Lock:
    if trader_id not in _trader_locks:
        _trader_locks[trader_id] = asyncio.Lock()
    return _trader_locks[trader_id]

# Save pre-market knowledge check interactions (every click)
@app.post("/save_premarket_interaction")
async def save_premarket_interaction(interaction: PremarketInteraction):
    try:
        lock = await _get_lock(interaction.trader_id)
        async with lock:
            data = _read_trader_data(interaction.trader_id)
            data["premarket_interactions"].append({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "question_index": interaction.question_index,
                "question_text": interaction.question_text,
                "selected_answer": interaction.selected_answer,
                "is_correct": interaction.is_correct,
            })
            _write_trader_data(interaction.trader_id, data)
        return success(message="Pre-market interaction saved")
    except Exception as e:
        return {"status": "error", "message": f"Failed to save pre-market interaction: {str(e)}"}

# Save post-market questionnaire responses
@app.get("/questionnaire/status")
async def questionnaire_status(trader_id: str = Query(...)):
    try:
        data = _read_trader_data(trader_id)
        completed = data.get("postmarket_responses") is not None
        return success(data={"completed": completed})
    except Exception:
        return success(data={"completed": False})

@app.post("/save_questionnaire_response")
async def save_questionnaire_response(response: QuestionnaireResponse):
    try:
        lock = await _get_lock(response.trader_id)
        async with lock:
            data = _read_trader_data(response.trader_id)

            if response.market_number is not None:
                # Per-market responses (2 questions: market_description, imbalance_reason)
                if "per_market_responses" not in data:
                    data["per_market_responses"] = {}
                data["per_market_responses"][str(response.market_number)] = {
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "market_description": response.responses[0] if len(response.responses) > 0 else None,
                    "imbalance_reason": response.responses[1] if len(response.responses) > 1 else None,
                }
            else:
                # Final questionnaire responses (q1-q4 + per-market questions for last market)
                data["postmarket_responses"] = {
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "q1": response.responses[0] if len(response.responses) > 0 else None,
                    "q2": response.responses[1] if len(response.responses) > 1 else None,
                    "q3": response.responses[2] if len(response.responses) > 2 else None,
                    "q4": response.responses[3] if len(response.responses) > 3 else None,
                    "market_description": response.responses[4] if len(response.responses) > 4 else None,
                    "imbalance_reason": response.responses[5] if len(response.responses) > 5 else None,
                }

            _write_trader_data(response.trader_id, data)
        return success(message="Questionnaire response saved successfully")
    except Exception as e:
        return {"status": "error", "message": f"Failed to save questionnaire response: {str(e)}"}

# Download all questionnaire data as zip of per-trader JSON files
@app.get("/admin/download_questionnaire_data")
async def download_questionnaire_data(current_user: dict = Depends(get_current_admin_user)):
    try:
        questionnaire_dir = _get_questionnaire_dir()
        json_files = list(questionnaire_dir.glob("*.json"))

        if not json_files:
            return Response(content="No questionnaire data found", media_type="text/plain")

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
            for f in json_files:
                zf.write(f, f.name)
        buf.seek(0)

        return StreamingResponse(
            buf,
            media_type="application/zip",
            headers={"Content-Disposition": "attachment; filename=questionnaire_data.zip"}
        )
    except Exception as e:
        return Response(
            content=f"Error downloading questionnaire data: {str(e)}",
            media_type="text/plain",
            status_code=500
        )

# Save consent form data
@app.post("/consent/save")
async def save_consent_data(consent: ConsentData):
    consent_dir = Path("logs/consent")
    consent_dir.mkdir(parents=True, exist_ok=True)
    consent_file = consent_dir / "consent_data.csv"
    file_exists = consent_file.exists()
    timestamp = datetime.now().isoformat()
    user_id = consent.user_id or consent.prolific_id
    user_type = consent.user_type or ("prolific" if consent.prolific_id else None)
    with open(consent_file, mode='a', newline='') as file:
        fieldnames = ['trader_id', 'user_id', 'user_type', 'consent_given', 'consent_timestamp']
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        trader_id = consent.trader_id or user_id
        row_data = {
            'trader_id': trader_id,
            'user_id': user_id,
            'user_type': user_type,
            'consent_given': str(consent.consent_given),
            'consent_timestamp': timestamp
        }
        writer.writerow(row_data)
    return success(message="Consent data saved successfully", timestamp=timestamp)


# Download consent data
@app.get("/admin/download-consent-data")
async def download_consent_data(current_user: dict = Depends(get_current_admin_user)):
    consent_dir = ROOT_DIR.parent / "logs/consent"
    consent_file = consent_dir / "consent_data.csv"
    if not consent_file.exists():
        return JSONResponse(status_code=404, content={"status": "error", "message": "Consent data file not found"})
    return FileResponse(path=consent_file, filename="consent_data.csv", media_type="text/csv")

# Generate lab session links
@app.post("/admin/generate-lab-links")
async def generate_lab_links(request: Request, current_user: dict = Depends(get_current_admin_user)):
    from .lab_auth import generate_lab_tokens, lab_trader_map, LAB_TOKENS
    try:
        body = await request.json()
        count = body.get("count", 10)
        num_treatments = body.get("num_treatments", 1)
        treatment_overrides = body.get("treatment_overrides", None)

        # Clear all previous lab state so re-generated tokens work
        LAB_TOKENS.clear()
        sm = market_handler.session_manager
        lab_usernames = [u for u in sm.user_historical_markets if u.startswith("LAB_")]
        for u in lab_usernames:
            sm.user_historical_markets.pop(u, None)
            sm.user_sessions.pop(u, None)
            sm.user_cohorts.pop(u, None)
            sm.user_ready_status.pop(u, None)
            sm.user_treatment_groups.pop(u, None)
        # Clear cohort state that was set up for previous lab cohorts
        sm.cohort_members.clear()
        sm.cohort_sessions.clear()
        sm.cohort_treatment_overrides.clear()
        sm.cohort_persistent_session_ids.clear()
        lab_trader_map.clear()

        # Use the request's base URL to construct lab links
        base_url = str(request.base_url).rstrip("/")
        # Frontend is typically on a different port; use origin header if available
        origin = request.headers.get("origin", base_url)
        links = generate_lab_tokens(count, base_url=origin, num_treatments=num_treatments)

        # Auto-set market_sizes to match treatments so each treatment group gets its own cohort
        if num_treatments > 1:
            block_size = count // num_treatments
            market_sizes = [block_size] * num_treatments
            sm.update_market_sizes(market_sizes)

        # Store cohort treatment overrides if provided
        # Format: {0: {"informed_trade_intensity": 0.36}, 1: {"informed_trade_intensity": 0.69}, ...}
        if treatment_overrides and isinstance(treatment_overrides, dict):
            for cohort_id_str, overrides in treatment_overrides.items():
                cohort_id = int(cohort_id_str)
                sm.cohort_treatment_overrides[cohort_id] = overrides

        return success(message=f"Generated {count} lab links ({num_treatments} treatments)", data={"links": links})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate lab links: {str(e)}")

# Set/get cohort treatment overrides for parallel treatment groups
@app.post("/admin/treatment-overrides")
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

@app.get("/admin/treatment-overrides")
async def get_treatment_overrides(current_user: dict = Depends(get_current_admin_user)):
    return success(data={"overrides": market_handler.session_manager.cohort_treatment_overrides})

# Get session type (unauthenticated, for login page to branch)
@app.get("/settings/session-type")
async def get_session_type():
    return success(data={"session_type": base_settings.get("session_type", "prolific")})

# Update Prolific settings in .env file
@app.post("/admin/prolific-settings")
async def update_prolific_settings(settings: ProlificSettings, current_user: dict = Depends(get_current_admin_user)):
    # Import the in-memory credentials storage
    from api.prolific_auth import IN_MEMORY_CREDENTIALS
    try:
        # Process and store credentials in memory if provided
        if "PROLIFIC_CREDENTIALS" in settings.settings:
            # Clear existing credentials
            IN_MEMORY_CREDENTIALS.clear()
            
            # Parse the credentials string
            creds_str = settings.settings["PROLIFIC_CREDENTIALS"]
            
            # Process each credential pair
            for cred_pair in creds_str.strip().split():
                parts = cred_pair.strip().split(",")
                if len(parts) == 2:
                    username, password = parts
                    IN_MEMORY_CREDENTIALS[username.strip()] = password.strip()
            
            print(f"Stored {len(IN_MEMORY_CREDENTIALS)} credential pairs in memory")
        
        env_path = Path(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))) / ".env"
        
        if not env_path.exists():
            return {
                "status": "error",
                "message": ".env file not found"
            }
        
        # Read the .env file
        env_content = env_path.read_text()
        
        # Update Prolific settings
        new_env_content = []
        prolific_credentials_updated = False
        prolific_study_id_updated = False
        prolific_redirect_url_updated = False
        
        for line in env_content.splitlines():
            # Skip updating PROLIFIC_CREDENTIALS in the .env file
            if line.startswith("PROLIFIC_CREDENTIALS="):
                # Don't include this line in the new content
                # We'll store credentials in memory instead
                prolific_credentials_updated = True
            elif line.startswith("PROLIFIC_STUDY_ID=") and "PROLIFIC_STUDY_ID" in settings.settings:
                new_env_content.append(f"PROLIFIC_STUDY_ID={settings.settings['PROLIFIC_STUDY_ID']}")
                prolific_study_id_updated = True
            elif line.startswith("PROLIFIC_REDIRECT_URL=") and "PROLIFIC_REDIRECT_URL" in settings.settings:
                new_env_content.append(f"PROLIFIC_REDIRECT_URL={settings.settings['PROLIFIC_REDIRECT_URL']}")
                prolific_redirect_url_updated = True
            else:
                new_env_content.append(line)
        
        # Add settings that weren't updated (they didn't exist in the file)
        # Skip adding PROLIFIC_CREDENTIALS to the .env file
        # We'll store credentials in memory instead
        
        if not prolific_study_id_updated and "PROLIFIC_STUDY_ID" in settings.settings:
            new_env_content.append(f"PROLIFIC_STUDY_ID={settings.settings['PROLIFIC_STUDY_ID']}")
        
        if not prolific_redirect_url_updated and "PROLIFIC_REDIRECT_URL" in settings.settings:
            new_env_content.append(f"PROLIFIC_REDIRECT_URL={settings.settings['PROLIFIC_REDIRECT_URL']}")
        
        # Write the updated content back to the .env file
        env_path.write_text("\n".join(new_env_content))
        
        return success(message="Prolific settings updated successfully")
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
