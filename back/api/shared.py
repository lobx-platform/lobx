"""
Shared state and helpers used across route modules.

All mutable global state lives here so route files can import it.
"""
import asyncio
from pathlib import Path
from typing import Dict

from core.data_models import TradingParameters
from core.simple_market_handler import SimpleMarketHandler
from utils.websocket_utils import sanitize_websocket_message  # re-export

# Initialize with default values from TradingParameters
default_params = TradingParameters()
base_settings = default_params.model_dump()

# Store accumulated rewards per user
accumulated_rewards: Dict[str, dict] = {}

# Central market handler (owns session_manager, trader_managers, etc.)
market_handler = SimpleMarketHandler()

# Trader order locks (prevent concurrent order processing for same trader)
trader_locks: Dict[str, asyncio.Lock] = {}

# Questionnaire per-trader locks
_trader_locks: Dict[str, asyncio.Lock] = {}

# Log directory root
ROOT_DIR = Path(__file__).resolve().parent.parent / "logs"


def get_historical_markets_count(username: str) -> int:
    return len(market_handler.user_historical_markets.get(username, set()))


def record_market_for_user(username: str, market_id: str):
    market_handler.user_historical_markets[username].add(market_id)


async def get_trader_lock(trader_id: str) -> asyncio.Lock:
    if trader_id not in trader_locks:
        trader_locks[trader_id] = asyncio.Lock()
    return trader_locks[trader_id]
