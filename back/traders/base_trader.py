"""
Refactored BaseTrader with explicit message handlers instead of dynamic dispatch.
"""
import asyncio
import uuid
from abc import abstractmethod
from typing import Dict, Any, Callable
from core.data_models import OrderType, ActionType, TraderType, ThrottleConfig
from utils.utils import setup_custom_logger

logger = setup_custom_logger(__name__)


class BaseTrader:
    """Base trader class with explicit message handling."""
    
    def __init__(self, trader_type: TraderType, id: str, cash=0, shares=0):
        # Core attributes
        self.initial_shares = shares
        self.initial_cash = cash
        self.cash = cash
        self.shares = shares
        self.trader_type = trader_type.value
        self.id = id
        self.trading_market_uuid = None

        # State management
        self._stop_requested = asyncio.Event()
        self.order_book: Dict = {}
        self.orders: list = []
        self.active_orders_in_book: list = []

        # PNL tracking
        self.DInv = []
        self.transaction_prices = []
        self.transaction_relevant_mid_prices = []
        self.general_mid_prices = []
        self.sum_cost = 0
        self.sum_dinv = 0
        self.sum_mid_executions = 0
        self.current_pnl = 0

        # Performance tracking
        self.start_time = asyncio.get_event_loop().time()
        self.filled_orders = []
        self.placed_orders = []

        # Goal tracking
        self.goal = 0
        self.goal_progress = 0

        # Throttling
        self.last_order_time = 0
        self.orders_in_window = 0
        self.throttle_config = None

        # Set up explicit message handlers instead of dynamic dispatch
        self.message_handlers = self._setup_message_handlers()

    def _setup_message_handlers(self) -> Dict[str, Callable]:
        """Set up explicit message handlers - no more dynamic dispatch."""
        return {
            "BOOK_UPDATED": self.on_book_updated,
            "TRADING_STARTED": self.on_trading_started,
            "closure": self.on_closure,
            "stop_trading": self.on_stop_trading,
            "transaction_update": self.on_transaction_update,
            "time_update": self.on_time_update,
        }

    # Explicit message handlers - replace handle_X pattern
    async def on_book_updated(self, data: Dict[str, Any]):
        """Handle book update messages."""
        # Default implementation - can be overridden
        pass

    async def on_trading_started(self, data: Dict[str, Any]):
        """Handle trading started messages."""
        # Reset the start time when trading actually begins
        self.start_time = asyncio.get_event_loop().time()

    async def on_closure(self, data: Dict[str, Any]):
        """Handle market closure."""
        self._stop_requested.set()
        await self.clean_up()

    async def on_stop_trading(self, data: Dict[str, Any]):
        """Handle stop trading signal."""
        # Send inventory report
        await self.send_to_trading_system({
            "action": "inventory_report",
            "trader_id": self.id,
            "shares": self.shares,
            "cash": self.cash,
        })
        self._stop_requested.set()

    async def on_transaction_update(self, data: Dict[str, Any]):
        """Handle transaction updates."""
        transactions = data.get("transactions", [])
        self.update_filled_orders(transactions)

    async def on_time_update(self, data: Dict[str, Any]):
        """Handle time updates."""
        # Default implementation - can be overridden
        pass

    # Core functionality methods
    async def on_message_from_system(self, data: Dict[str, Any]):
        """Process messages from the trading platform - no more dynamic dispatch."""
        try:
            message_type = data.get("type")
            
            # Update mid price if available
            if data.get("midpoint"):
                self.update_mid_price(data["midpoint"])

            if not data:
                return

            # Update order book
            order_book = data.get("order_book")
            if order_book:
                self.order_book = order_book

            # Update active orders
            active_orders_in_book = data.get("active_orders")
            if active_orders_in_book:
                self.active_orders_in_book = active_orders_in_book
                own_orders = [
                    order for order in active_orders_in_book if order["trader_id"] == self.id
                ]
                self.orders = own_orders

            # Use explicit handler lookup instead of getattr
            handler = self.message_handlers.get(message_type)
            if handler:
                await handler(data)
            else:
                if message_type and message_type not in ['BOOK_UPDATED', 'time_update']:
                    logger.warning(f"[{self.id}] No handler for message type: {message_type}")

            # Call post-processing hook
            await self.post_processing_server_message(data)

        except Exception as e:
            logger.error(f"[{self.id}] Error processing message: {e}")
            import traceback
            traceback.print_exc()

    async def initialize(self):
        """Initialize the trader."""
        if hasattr(self, 'params'):
            # Get throttle config for this trader type
            self.throttle_config = self.params.get('throttle_settings', {}).get(self.trader_type, None)
            if self.throttle_config:
                self.throttle_config = ThrottleConfig(**self.throttle_config)
            else:
                self.throttle_config = ThrottleConfig()  # Default no throttling

    async def clean_up(self):
        """Clean up trader resources."""
        self._stop_requested.set()

    async def connect_to_market(self, trading_market_uuid: str, trading_market=None):
        """Connect trader to market."""
        await self.initialize()
        self.trading_market_uuid = trading_market_uuid
        self.trading_market = trading_market

    async def send_to_trading_system(self, message: Dict[str, Any]):
        """Send message to trading platform."""
        message["trader_id"] = self.id
        if hasattr(self, 'trading_market') and self.trading_market:
            await self.trading_market.handle_trader_message(message)

    # PNL and performance tracking
    def get_elapsed_time(self) -> float:
        """Get elapsed time since trader started."""
        current_time = asyncio.get_event_loop().time()
        return current_time - self.start_time

    def get_vwap(self) -> float:
        """Get volume-weighted average price."""
        return (
            sum(self.transaction_prices) / len(self.transaction_prices)
            if self.transaction_prices
            else 0
        )

    def update_mid_price(self, new_mid_price: float):
        """Update the mid price tracking."""
        self.general_mid_prices.append(new_mid_price)

    def update_data_for_pnl(self, dinv: float, transaction_price: float) -> None:
        """Update PNL calculations."""
        relevant_mid_price = (
            self.general_mid_prices[-1]
            if self.general_mid_prices
            else transaction_price
        )

        self.DInv.append(dinv)
        self.transaction_prices.append(transaction_price)
        self.transaction_relevant_mid_prices.append(relevant_mid_price)

        self.sum_cost += dinv * (transaction_price - relevant_mid_price)
        self.sum_dinv += dinv
        self.sum_mid_executions += relevant_mid_price * dinv

        self.current_pnl = (
            relevant_mid_price * self.sum_dinv - self.sum_mid_executions - self.sum_cost
        )

    def get_current_pnl(self, use_latest_general_mid_price=True) -> float:
        """Get current PNL."""
        if use_latest_general_mid_price and self.general_mid_prices:
            latest_mid_price = self.general_mid_prices[-1]
            pnl_adjusted = (
                latest_mid_price * self.sum_dinv
                - self.sum_mid_executions
                - self.sum_cost
            )
            return pnl_adjusted
        return self.current_pnl

    @property
    def delta_cash(self) -> float:
        """Get change in cash from initial."""
        return self.cash - self.initial_cash

    def update_filled_orders(self, transactions: list):
        """Update filled orders from transactions."""
        for transaction in transactions:
            if transaction["trader_id"] == self.id:
                filled_order = {
                    "id": transaction["id"],
                    "price": transaction["price"],
                    "amount": transaction["amount"],
                    "type": transaction["type"],
                    "timestamp": transaction.get("timestamp", None),
                }
                self.filled_orders.append(filled_order)

                self.update_inventory([transaction])
                self.update_goal_progress(transaction)

                self.update_data_for_pnl(
                    transaction["amount"]
                    if transaction["type"] == "bid"
                    else -transaction["amount"],
                    transaction["price"],
                )

    def update_inventory(self, transactions_relevant_to_self: list) -> None:
        """Update trader inventory from transactions with floor checks.

        Note: The primary validation happens in post_new_order() which blocks
        orders that would exceed available shares/cash. This method adds a
        defensive safety net that clamps values to prevent negative inventory
        in case of race conditions or edge cases.
        """
        for transaction in transactions_relevant_to_self:
            if transaction["type"] == "bid":
                cost = transaction["price"] * transaction["amount"]
                new_cash = self.cash - cost
                if new_cash < 0:
                    logger.error(
                        f"NEGATIVE CASH BLOCKED: trader {self.id} would have {new_cash} cash "
                        f"after buying {transaction['amount']} shares at {transaction['price']}. "
                        f"Current cash: {self.cash}, cost: {cost}. Clamping to 0."
                    )
                    new_cash = 0  # Clamp to prevent negative cash
                self.shares += transaction["amount"]
                self.cash = new_cash
            elif transaction["type"] == "ask":
                new_shares = self.shares - transaction["amount"]
                if new_shares < 0:
                    logger.error(
                        f"NEGATIVE INVENTORY BLOCKED: trader {self.id} would have {new_shares} shares "
                        f"after selling {transaction['amount']} shares. "
                        f"Current shares: {self.shares}, initial_shares: {self.initial_shares}. Clamping to 0."
                    )
                    new_shares = 0  # Clamp to prevent negative inventory
                self.shares = new_shares
                self.cash += transaction["price"] * transaction["amount"]

    def update_goal_progress(self, transaction: Dict[str, Any]):
        """Update progress towards the trader's goal."""
        if self.goal == 0:  # No goal to track
            return

        amount = transaction.get('amount', 1)
        if transaction['type'] == 'bid':
            self.goal_progress += amount
        elif transaction['type'] == 'ask':
            self.goal_progress -= amount

    def get_available_cash(self) -> float:
        """Calculate available cash considering locked orders.

        Includes both:
        - Orders confirmed in the order book (self.orders)
        - Orders placed but not yet confirmed (self.placed_orders)
        This prevents race conditions where rapid orders bypass validation.
        """
        # Cash locked by confirmed orders in the book
        locked_in_book = sum(
            order["price"] * order["amount"]
            for order in self.orders
            if order["order_type"] == OrderType.BID
        )
        # Cash locked by orders we've placed but not yet confirmed
        # (prevents race condition between placing order and receiving BOOK_UPDATED)
        locked_pending = sum(
            order["price"] * order["amount"]
            for order in self.placed_orders
            if order.get("order_type") == OrderType.BID
            # Only count if not already filled (check if order_ids still exist)
            and not any(oid in [o["id"] for o in self.filled_orders] for oid in order.get("order_ids", []))
            # Only count if not already in self.orders (avoid double counting)
            and not any(oid in [o["id"] for o in self.orders] for oid in order.get("order_ids", []))
        )
        return self.cash - locked_in_book - locked_pending

    def get_available_shares(self) -> int:
        """Calculate available shares considering locked orders.

        Includes both:
        - Orders confirmed in the order book (self.orders)
        - Orders placed but not yet confirmed (self.placed_orders)
        This prevents race conditions where rapid orders bypass validation.
        """
        # Shares locked by confirmed orders in the book
        locked_in_book = sum(
            order["amount"]
            for order in self.orders
            if order["order_type"] == OrderType.ASK
        )
        # Shares locked by orders we've placed but not yet confirmed
        # (prevents race condition between placing order and receiving BOOK_UPDATED)
        locked_pending = sum(
            order["amount"]
            for order in self.placed_orders
            if order.get("order_type") == OrderType.ASK
            # Only count if not already filled
            and not any(oid in [o["id"] for o in self.filled_orders] for oid in order.get("order_ids", []))
            # Only count if not already in self.orders (avoid double counting)
            and not any(oid in [o["id"] for o in self.orders] for oid in order.get("order_ids", []))
        )
        return self.shares - locked_in_book - locked_pending

    # Order management
    async def post_new_order(self, amount: int, price: int, order_type: OrderType) -> str:
        """Post a new order with throttling if configured."""
        # Check balance for human and agentic traders (noise/informed traders have infinite resources)
        # This prevents negative inventory issues
        traders_with_finite_resources = [TraderType.HUMAN.value]
        if self.trader_type in traders_with_finite_resources:
            if order_type == OrderType.BID:
                # buying - check if enough cash (including locked cash in active orders)
                available_cash = self.get_available_cash()
                if available_cash < price * amount:
                    logger.warning(
                        f"trader {self.id} ({self.trader_type}) insufficient cash: "
                        f"available {available_cash}, needs {price * amount}"
                    )
                    return None
            elif order_type == OrderType.ASK:
                # selling - check if enough shares (including locked shares in active orders)
                available_shares = self.get_available_shares()
                if available_shares < amount:
                    logger.warning(
                        f"trader {self.id} ({self.trader_type}) insufficient shares: "
                        f"available {available_shares}, needs {amount}, current shares: {self.shares}"
                    )
                    return None

        # Apply throttling if configured
        if self.throttle_config and self.throttle_config.order_throttle_ms > 0:
            current_time = asyncio.get_event_loop().time() * 1000  # Convert to milliseconds

            # Check if we're in a new window
            if current_time - self.last_order_time > self.throttle_config.order_throttle_ms:
                self.last_order_time = current_time
                self.orders_in_window = 0

            # Check if we've exceeded the order limit in this window
            if self.orders_in_window >= self.throttle_config.max_orders_per_window:
                return None  # Discard the order

            # Increment order count for this window
            self.orders_in_window += 1

        # Special handling for zero-amount orders (only for human traders)
        if amount == 0 and self.trader_type == TraderType.HUMAN.value:
            # Create a special zero-amount order for record-keeping purposes
            order_id = f"{self.id}_zero_amount_{len(self.placed_orders)}"
            new_order = {
                "action": ActionType.POST_NEW_ORDER.value,
                "amount": 0,
                "price": price,
                "order_type": order_type,
                "order_id": order_id,
                "is_record_keeping": True,  # Flag to indicate this is for record-keeping only
            }

            await self.send_to_trading_system(new_order)

            self.placed_orders.append({
                "order_ids": [order_id],
                "amount": 0,
                "price": price,
                "order_type": order_type,
                "timestamp": asyncio.get_event_loop().time(),
                "is_record_keeping": True,
            })

            return order_id

        # Regular order processing
        order_id = f"{self.id}_{len(self.placed_orders)}"
        new_order = {
            "action": ActionType.POST_NEW_ORDER.value,
            "amount": amount,
            "price": price,
            "order_type": order_type,
            "order_id": order_id,
        }

        await self.send_to_trading_system(new_order)

        self.placed_orders.append({
            "order_ids": [order_id],
            "amount": amount,
            "price": price,
            "order_type": order_type,
            "timestamp": asyncio.get_event_loop().time(),
        })

        return order_id

    async def send_cancel_order_request(self, order_id: uuid.UUID) -> bool:
        """Send cancel order request."""
        if not order_id:
            return False
        if not self.orders:
            return False
        if order_id not in [order["id"] for order in self.orders]:
            return False

        order_to_cancel = next(
            (order for order in self.orders if order["id"] == order_id), None
        )

        if self.trader_type != TraderType.NOISE.value:
            if order_to_cancel["order_type"] == OrderType.BID:
                self.cash += order_to_cancel["price"] * order_to_cancel["amount"]
            elif order_to_cancel["order_type"] == OrderType.ASK:
                self.shares += order_to_cancel["amount"]

        cancel_order_request = {
            "action": ActionType.CANCEL_ORDER.value,
            "trader_id": self.id,
            "order_id": order_id,
            "amount": -order_to_cancel["amount"],
            "price": order_to_cancel["price"],
            "order_type": order_to_cancel["order_type"],
        }

        try:
            await self.send_to_trading_system(cancel_order_request)
            return True
        except Exception:
            return False

    # Abstract methods
    @abstractmethod
    async def post_processing_server_message(self, json_message: Dict[str, Any]):
        """Post-process server messages - implement in subclasses."""
        pass

    async def run(self):
        """Main trader loop - implement in subclasses."""
        pass


class PausingTrader(BaseTrader):
    """Trader with sleep/pause functionality for research studies."""
    
    def __init__(self, trader_type: TraderType, id: str, cash=0, shares=0):
        super().__init__(trader_type, id, cash, shares)
        self.sleep_duration = 0
        self.sleep_interval = 60
        self.last_sleep_time = 0
        self.total_sleep_time = 0

    async def initialize(self):
        """Initialize with sleep parameters from params."""
        await super().initialize()
        if hasattr(self, 'params'):
            self.sleep_duration = self.params.get('sleep_duration', 0)
            self.sleep_interval = self.params.get('sleep_interval', 60)

    async def maybe_sleep(self):
        """Check if it's time to sleep and handle sleep/wake status updates."""
        if self.sleep_duration <= 0 or self.sleep_interval <= 0:
            return
            
        current_time = asyncio.get_event_loop().time()
        raw_elapsed = current_time - self.start_time
        
        if raw_elapsed - self.last_sleep_time >= self.sleep_interval:
            self.last_sleep_time = raw_elapsed
            
            # Send sleep status
            await self._send_status_update("sleeping")
            
            # Sleep
            sleep_start = asyncio.get_event_loop().time()
            await asyncio.sleep(self.sleep_duration)
            self.total_sleep_time += asyncio.get_event_loop().time() - sleep_start
            
            # Send wake status
            await self._send_status_update("active")

    def is_algo_sleeping(self):
        """Check if algo traders are currently sleeping."""
        if self.sleep_duration <= 0 or self.sleep_interval <= 0:
            return False
            
        current_time = asyncio.get_event_loop().time()
        raw_elapsed = current_time - self.start_time
        
        # Calculate if we're in a sleep period
        time_since_last_interval = raw_elapsed % self.sleep_interval
        return time_since_last_interval < self.sleep_duration

    def should_human_be_paused(self):
        """Human should be paused when algos are active (not sleeping)."""
        return not self.is_algo_sleeping()

    async def _send_status_update(self, status: str):
        """Send trader status update to the platform."""
        if hasattr(self, 'trading_market') and self.trading_market:
            await self.trading_market.handle_trader_message({
                "action": "status_update",
                "trader_id": self.id,
                "trader_status": status,
                "is_status_update": True
            })

    def get_effective_elapsed_time(self) -> float:
        """Get elapsed time excluding sleep periods."""
        raw_elapsed = super().get_elapsed_time()
        return max(0, raw_elapsed - self.total_sleep_time)


# Backward compatibility - can be removed after migration
BaseTrader.handle_closure = BaseTrader.on_closure
BaseTrader.handle_stop_trading = BaseTrader.on_stop_trading
BaseTrader.handle_TRADING_STARTED = BaseTrader.on_trading_started 