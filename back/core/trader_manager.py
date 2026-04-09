"""
trader manager: connects and manages human traders

launches new trading markets when clients ask for them
helps find existing traders and returns their ids
"""

from .data_models import TradingParameters, OrderType, ActionType, TraderType, TraderRole
from typing import List, Optional
from traders import (
    HumanTrader,
    NoiseTrader,
    InformedTrader,
    BookInitializer,
)
from .trading_platform import TradingPlatform
import asyncio
import os
from utils import setup_custom_logger
import time
import random

logger = setup_custom_logger(__name__)

class TraderManager:
    params: TradingParameters
    trading_system: TradingPlatform = None
    traders = {}
    human_traders = List[HumanTrader]
    noise_traders = List[NoiseTrader]
    informed_traders = List[InformedTrader]
    human_informed_trader = None  # Track the human trader with INFORMED role in this market

    def __init__(self, params: TradingParameters, market_id: str = None):
        self.params = params
        self.tasks = []
        self.human_informed_trader = None  # Keep only for tracking human trader with INFORMED role
        self.human_traders = []
        
        params_dict = params.model_dump()  # Convert to dict for easier access
        
        # Create traders (Human + Informed + Noise only)
        self.book_initializer = self._create_book_initializer(params)
        self.noise_traders = self._create_noise_traders(params.num_noise_traders, params_dict)
        self.informed_traders = self._create_informed_traders(params.num_informed_traders, params_dict)

        # Combine all traders into one dict
        self.traders = {
            t.id: t
            for t in self.noise_traders
            + self.informed_traders
            + [self.book_initializer]
        }
        
        # Create trading market
        # Use provided market_id or generate one with timestamp
        if market_id is None:
            current_timestamp = int(time.time())
            market_id = f"MARKET_{current_timestamp}"
        
        self.trading_market = TradingPlatform(
            market_id=market_id,
            duration=params.trading_day_duration,
            default_price=params.default_price,
            params=params_dict  # Pass dict
        )

    def _create_book_initializer(self, params: TradingParameters):
        return BookInitializer(id="BOOK_INITIALIZER", trader_creation_data=params.model_dump())

    def _create_noise_traders(self, n_noise_traders: int, params: dict):
        return [
            NoiseTrader(
                id=f"NOISE_{i+1}",
                params=params,
            )
            for i in range(n_noise_traders)
        ]

    def _create_informed_traders(self, n_informed_traders: int, params: dict):
        if n_informed_traders <= 0:
            return []
            
        traders = [
            InformedTrader(
                id=f"INFORMED_{i+1}",
                params=dict(params),  # copy so each trader can have independent direction
            )
            for i in range(n_informed_traders)
        ]
        
        return traders

    async def add_human_trader(self, gmail_username: str, role: TraderRole, goal: Optional[int] = None) -> str:
        """Add human trader with specified role and goal"""
        trader_id = f"HUMAN_{gmail_username}"
        
        if trader_id in self.traders:
            return trader_id

        new_trader = HumanTrader(
            id=trader_id,
            cash=self.params.initial_cash,
            shares=self.params.initial_stocks,
            goal=goal,
            role=role,
            trading_market=self.trading_market,
            params=self.params.model_dump(),
            gmail_username=gmail_username
        )
        
        if role == TraderRole.INFORMED:
            # Allow multiple human informed traders
            self.human_informed_trader = new_trader

        self.traders[trader_id] = new_trader
        self.human_traders.append(new_trader)
        
        return trader_id

    async def set_trader_goal(self, trader_id: str, goal: int):
        """give trader a new goal"""
        trader = self.traders.get(trader_id)
        if trader and isinstance(trader, HumanTrader):
            trader.goal = goal
            return True
        return False

    async def launch(self):
        await self.trading_market.initialize()

        for trader_id, trader in self.traders.items():
            await trader.initialize()

            if not isinstance(trader, HumanTrader):
                await trader.connect_to_market(
                    trading_market_uuid=self.trading_market.id,
                    trading_market=self.trading_market
                )
                
                # Register AI trader with the trading platform
                await self.trading_market.handle_register_me({
                    "trader_id": trader.id,
                    "trader_type": trader.trader_type,
                    "gmail_username": None,
                    "trader_instance": trader
                })

        await self.book_initializer.initialize_order_book()

        self.trading_market.set_initialization_complete()

        # Wait for all required traders based on predefined_goals length
        num_required_traders = len(self.params.predefined_goals)
        
        # Check if any of the human traders is a Prolific user
        has_prolific_user = any("prolific" in trader.id.lower() for trader in self.human_traders)
        
        # Skip waiting if we have a Prolific user, otherwise wait for all required traders
        if not has_prolific_user:
            while len(self.human_traders) < num_required_traders:
                await asyncio.sleep(1)

        await self.trading_market.start_trading()

        trading_market_task = asyncio.create_task(self.trading_market.run())
        trader_tasks = [asyncio.create_task(i.run()) for i in self.traders.values()]

        self.tasks.append(trading_market_task)
        self.tasks.extend(trader_tasks)

        await trading_market_task

    async def cleanup(self):
        await self.trading_market.clean_up()
        for trader in self.traders.values():
            await trader.clean_up()
        for task in self.tasks:
            task.cancel()  # bye bye tasks
        await asyncio.gather(*self.tasks, return_exceptions=True)
        self.tasks.clear()  # clean slate

    def get_trader(self, trader_id):
        trader = self.traders.get(trader_id)
        if trader and isinstance(trader, HumanTrader):
            # get their stats too
            trader_info = trader.get_trader_params_as_dict()
            return trader
        return trader

    def exists(self, trader_id):
        return trader_id in self.traders

    def get_params(self):
        params = self.params.model_dump()
        trading_market_params = self.trading_market.get_params()
        params.update(trading_market_params)
        return params
