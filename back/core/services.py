"""
Service layer for trading platform - pure business logic separated from side effects.
"""
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime, timezone
import uuid
import asyncio

from .data_models import Order, OrderStatus, OrderType, TransactionModel
from .orderbook_manager import OrderBookManager
from .transaction_manager import TransactionManager


@dataclass
class OrderResult:
    """Result of order processing."""
    order: Dict[str, Any]
    immediately_matched: bool
    matches: List[Tuple[Dict, Dict, float]] = None
    
    def __post_init__(self):
        if self.matches is None:
            self.matches = []


@dataclass
class CancelResult:
    """Result of order cancellation."""
    success: bool
    order_id: str
    order: Optional[Dict[str, Any]] = None
    reason: Optional[str] = None


@dataclass
class TransactionResult:
    """Result of transaction creation."""
    transaction: TransactionModel
    transaction_details: Dict[str, Any]
    ask_trader_id: str
    bid_trader_id: str


class OrderService:
    """Pure business logic for order processing."""
    
    def __init__(self, order_book_manager: OrderBookManager, pricing_service: 'PricingService'):
        self.order_book = order_book_manager
        self.pricing = pricing_service
    
    async def process_order(self, order_data: Dict[str, Any]) -> OrderResult:
        """Process an order without side effects."""
        # Data transformation
        order_data["order_type"] = int(order_data["order_type"])
        order_id = order_data.get("order_id")
        if order_id:
            order_data["id"] = order_id
        
        # Handle zero-amount orders (record-keeping)
        is_record_keeping = order_data.get("is_record_keeping", False)
        if order_data.get("amount") == 0 and is_record_keeping:
            record_order = {
                "id": order_data.get("id", str(uuid.uuid4())),
                "trader_id": order_data.get("trader_id"),
                "order_type": order_data.get("order_type"),
                "price": order_data.get("price"),
                "amount": 0,
                "timestamp": datetime.now(timezone.utc).timestamp(),
                "is_record_keeping": True
            }
            return OrderResult(order=record_order, immediately_matched=False)
        
        # Create order
        order_creation_data = {**order_data}
        order_creation_data["status"] = OrderStatus.BUFFERED.value
        order = Order(**order_creation_data)
        order_dict = order.model_dump()
        
        # Add informed trader progress if present
        informed_trader_progress = order_data.get("informed_trader_progress")
        if informed_trader_progress is not None:
            order_dict["informed_trader_progress"] = informed_trader_progress
        
        order_dict["id"] = str(order_dict["id"])
        
        # Place order in order book
        placed_order, immediately_matched = self.order_book.place_order(order_dict)
        
        # Get matches if immediately matched
        matches = []
        if immediately_matched:
            matches = self.order_book.clear_orders()
        
        return OrderResult(
            order=placed_order,
            immediately_matched=immediately_matched,
            matches=matches
        )
    
    async def cancel_order(self, order_id: str) -> CancelResult:
        """Cancel an order."""
        order, success = self.order_book.cancel_order_with_details(order_id)
        
        if success:
            return CancelResult(success=True, order_id=order_id, order=order)
        else:
            return CancelResult(
                success=False, 
                order_id=order_id, 
                order=order,
                reason="Order not found or cancellation failed"
            )


class TransactionService:
    """Service for handling transaction creation and processing."""
    
    def __init__(self, transaction_manager: TransactionManager):
        self.transaction_manager = transaction_manager
    
    async def create_transaction(self, bid: Dict, ask: Dict, transaction_price: float) -> TransactionResult:
        """Create a transaction from matched orders."""
        ask_trader_id, bid_trader_id, transaction, transaction_details = \
            await self.transaction_manager.create_transaction(bid, ask, transaction_price)
        
        return TransactionResult(
            transaction=transaction,
            transaction_details=transaction_details,
            ask_trader_id=ask_trader_id,
            bid_trader_id=bid_trader_id
        )
    
    async def process_matches(self, matches: List[Tuple[Dict, Dict, float]]) -> List[TransactionResult]:
        """Process multiple matched orders into transactions."""
        results = []
        for ask, bid, transaction_price in matches:
            result = await self.create_transaction(bid, ask, transaction_price)
            results.append(result)
        return results


class PricingService:
    """Service for price calculations."""
    
    def __init__(self, default_price: int, default_spread: int, punishing_constant: int):
        self.default_price = default_price
        self.default_spread = default_spread
        self.punishing_constant = punishing_constant
        self._current_price = 0
    
    @property
    def mid_price(self) -> float:
        """Get the mid price."""
        return self._current_price or self.default_price
    
    def update_current_price(self, price: float):
        """Update the current price."""
        self._current_price = price
    
    def calculate_closure_price(self, shares: int, order_type: OrderType) -> float:
        """Calculate the closure price for a given order."""
        return (
            self.mid_price
            + order_type * shares * self.default_spread * self.punishing_constant
        )


class TraderService:
    """Service for trader management."""
    
    def __init__(self):
        self.connected_traders: Dict[str, Dict] = {}
        self.trader_responses: Dict[str, bool] = {}
    
    async def register_trader(self, trader_id: str, trader_type: str, 
                            gmail_username: Optional[str], trader_instance: Any) -> Dict[str, Any]:
        """Register a new trader."""
        self.connected_traders[trader_id] = {
            "trader_type": trader_type,
            "gmail_username": gmail_username,
            "trader_instance": trader_instance,
        }
        self.trader_responses[trader_id] = False
        
        return {
            "respond": True,
            "trader_id": trader_id,
            "message": "Registered successfully",
            "individual": True,
        }
    
    async def process_inventory_report(self, trader_id: str, shares: int, 
                                     pricing_service: PricingService) -> List[Order]:
        """Process trader inventory report and generate closure orders."""
        # Mark trader as responded
        self.trader_responses[trader_id] = True
        
        # Validate trader exists
        if trader_id not in self.connected_traders:
            return []
        
        trader_type = self.connected_traders[trader_id].get("trader_type")
        if not trader_type:
            return []
        
        # Generate closure orders if trader has shares
        orders = []
        if shares != 0:
            trader_order_type = OrderType.ASK if shares > 0 else OrderType.BID
            platform_order_type = OrderType.BID if shares > 0 else OrderType.ASK
            shares_abs = abs(shares)
            closure_price = pricing_service.calculate_closure_price(shares_abs, trader_order_type)
            
            # Create orders for both trader and platform
            proto_order = {
                "amount": shares_abs,
                "price": closure_price,
                "status": OrderStatus.BUFFERED.value,
                "market_id": "CLOSURE",  # Will be set by caller
            }
            
            trader_order = Order(
                trader_id=trader_id, 
                order_type=trader_order_type, 
                **proto_order
            )
            platform_order = Order(
                trader_id="PLATFORM",  # Will be set by caller
                order_type=platform_order_type, 
                **proto_order
            )
            
            orders.append((trader_order, platform_order, closure_price))
        
        return orders
    
    def get_connected_traders(self) -> List[str]:
        """Get list of connected trader IDs."""
        return list(self.connected_traders.keys())
    
    def get_trader_info(self, trader_id: str) -> Optional[Dict]:
        """Get trader information."""
        return self.connected_traders.get(trader_id)


class BroadcastService:
    """Service for managing broadcasts and notifications."""

    def __init__(self, order_book_manager: OrderBookManager,
                 transaction_manager: TransactionManager, pricing_service: PricingService):
        self.order_book = order_book_manager
        self.transaction_manager = transaction_manager
        self.pricing = pricing_service
        self.websockets = set()
        self.connected_traders: Dict[str, Dict] = {}
        self._market_id: Optional[str] = None  # set by MarketOrchestrator for SIO room emit
    
    def register_websocket(self, websocket):
        """Register a WebSocket connection."""
        self.websockets.add(websocket)
    
    def unregister_websocket(self, websocket):
        """Unregister a WebSocket connection."""
        self.websockets.discard(websocket)
    
    def set_trader_registry(self, connected_traders: Dict[str, Dict]):
        """Set reference to trader registry."""
        self.connected_traders = connected_traders
    
    async def broadcast_to_websockets(self, message: Dict[str, Any]):
        """Broadcast message to all WebSocket connections and Socket.IO room."""
        from utils.websocket_utils import sanitize_websocket_message
        sanitized_message = sanitize_websocket_message(message)

        # Socket.IO room broadcast (if a market_id is set)
        if self._market_id:
            try:
                from api.socketio_server import emit_to_market
                msg_type = sanitized_message.get("type", "update")
                await emit_to_market(self._market_id, msg_type.lower(), sanitized_message)
            except Exception as e:
                print(f"Error emitting Socket.IO broadcast: {e}")

        # Legacy raw-WebSocket broadcast
        if not self.websockets:
            return

        disconnected = set()
        for websocket in self.websockets.copy():
            try:
                await websocket.send_json(sanitized_message)
            except Exception as e:
                print(f"Error sending WebSocket message: {e}")
                disconnected.add(websocket)

        for websocket in disconnected:
            self.websockets.discard(websocket)
    

    
    async def send_to_traders(self, message: Dict[str, Any], trader_list: Optional[List[str]] = None):
        """Send message to specific traders or all traders."""
        if trader_list is None:
            trader_list = list(self.connected_traders.keys())
        
        for trader_id in trader_list:
            trader_info = self.connected_traders.get(trader_id)
            if trader_info and 'trader_instance' in trader_info:
                trader = trader_info['trader_instance']
                try:
                    await trader.on_message_from_system(message)
                except Exception:
                    pass  # Continue to other traders
    
    async def create_broadcast_message(self, message_type: str, base_message: Dict[str, Any],
                                     start_time: Optional[datetime], duration: int,
                                     incoming_message: Optional[Dict] = None) -> Dict[str, Any]:
        """Create a complete broadcast message with all market data."""
        current_time = datetime.now(timezone.utc)
        
        message = {
            "type": message_type,
            "current_time": current_time.isoformat(),
            "start_time": start_time.isoformat() if start_time else None,
            "duration": duration,
            "order_book": self.order_book.get_order_book_snapshot(),
            "active_orders": self.order_book.get_active_orders_to_broadcast(),
            "history": self.transaction_manager.transactions,
            "spread": self.order_book.get_spread()[0],
            "midpoint": self.order_book.get_spread()[1],
            "transaction_price": self.transaction_manager.transaction_price,
            "incoming_message": incoming_message,
            "informed_trader_progress": incoming_message.get("informed_trader_progress") if incoming_message else None,
            **base_message
        }
        
        if message_type == "FILLED_ORDER" and incoming_message:
            message["matched_orders"] = incoming_message.get("matched_orders")
        
        return message 