"""
Event handlers for trading platform - orchestrate services and manage side effects.
"""
from typing import Dict, Any, Optional
from datetime import datetime
import asyncio
from utils.utils import setup_custom_logger

from .events import (
    EventHandler, TradingEvent, OrderPlacedEvent, OrderCancelledEvent,
    TraderRegisteredEvent, InventoryReportEvent,
)
from .services import (
    OrderService, TransactionService, PricingService, TraderService, BroadcastService,
    OrderResult, CancelResult,
)
from .data_models import OrderType

logger = setup_custom_logger(__name__)


class OrderHandler(EventHandler):
    """Handles order placement events."""
    
    def __init__(self, order_service: OrderService, transaction_service: TransactionService,
                 broadcast_service: BroadcastService, trading_logger, order_lock: asyncio.Lock,
                 market_id: str, is_active_func):
        self.order_service = order_service
        self.transaction_service = transaction_service
        self.broadcast_service = broadcast_service
        self.trading_logger = trading_logger
        self.order_lock = order_lock
        self.market_id = market_id
        self.is_active_func = is_active_func
    
    async def handle(self, event: OrderPlacedEvent) -> Optional[Dict[str, Any]]:
        """Handle order placement with concurrency control."""
        # Check if market is active
        if not self.is_active_func():
            logger.critical("Order placement skipped because the trading market is not active.")
            return {"status": "error", "message": "Market not active"}
        
        async with self.order_lock:
            return await self._process_order(event)
    
    async def _process_order(self, event: OrderPlacedEvent) -> Dict[str, Any]:
        """Process order placement."""
        # Set market ID
        event.order_data["market_id"] = self.market_id
        
        # Process order through service
        result: OrderResult = await self.order_service.process_order(event.order_data)
        
        # Handle record-keeping orders
        if result.order.get("is_record_keeping"):
            self.trading_logger.info(f"RECORD_KEEPING_ORDER: {result.order}")
            return {
                "type": "RECORD_KEEPING_ORDER",
                "content": "Record keeping order processed",
                "respond": True,
                "informed_trader_progress": event.informed_progress,
            }
        
        # Log the order
        self.trading_logger.info(f"ADD_ORDER: {result.order}")
        
        # Process immediate matches
        if result.immediately_matched and result.matches:
            transaction_results = await self.transaction_service.process_matches(result.matches)
            
            # Log matched orders
            for ask, bid, transaction_price in result.matches:
                match_data = {
                    "bid_order_id": str(bid["id"]),
                    "ask_order_id": str(ask["id"]),
                    "transaction_price": transaction_price,
                    "amount": min(bid["amount"], ask["amount"])
                }
                self.trading_logger.info(f"MATCHED_ORDER: {match_data}")
            
            # Broadcast transactions
            for tx_result in transaction_results:
                await self.broadcast_service.broadcast_to_websockets(tx_result.transaction_details)
                await self.broadcast_service.send_to_traders(tx_result.transaction_details)
        
        # Broadcast order book update
        message = await self.broadcast_service.create_broadcast_message(
            "BOOK_UPDATED",
            {"order_added": True},
            None,  # start_time will be set elsewhere
            0,     # duration will be set elsewhere
            {"informed_trader_progress": event.informed_progress}
        )
        
        await self.broadcast_service.broadcast_to_websockets(message)
        await self.broadcast_service.send_to_traders(message)
        
        return {
            "type": "ADDED_ORDER",
            "content": "A",
            "respond": True,
            "informed_trader_progress": event.informed_progress,
        }


class CancelHandler(EventHandler):
    """Handles order cancellation events."""
    
    def __init__(self, order_service: OrderService, broadcast_service: BroadcastService,
                 trading_logger, is_active_func):
        self.order_service = order_service
        self.broadcast_service = broadcast_service
        self.trading_logger = trading_logger
        self.is_active_func = is_active_func
    
    async def handle(self, event: OrderCancelledEvent) -> Optional[Dict[str, Any]]:
        """Handle order cancellation."""
        # Check if market is active
        if not self.is_active_func():
            logger.critical("Order cancellation skipped because the trading market is not active.")
            return {"status": "error", "message": "Market not active"}
        
        try:
            # Cancel order through service
            result: CancelResult = await self.order_service.cancel_order(event.order_id)
            
            if result.success:
                # Log cancellation with complete order details
                self.trading_logger.info(f"CANCEL_ORDER: {result.order}")
                
                # Broadcast update
                message = await self.broadcast_service.create_broadcast_message(
                    "BOOK_UPDATED",
                    {"order_cancelled": True, "order_id": event.order_id},
                    None, 0  # timing info will be set elsewhere
                )
                
                await self.broadcast_service.broadcast_to_websockets(message)
                await self.broadcast_service.send_to_traders(message)
                
                return {
                    "status": "cancel success",
                    "order_id": event.order_id,
                    "type": "ORDER_CANCELLED",
                    "respond": True,
                }
            else:
                return {
                    "status": "failed",
                    "reason": result.reason,
                }
        
        except Exception as e:
            return {"status": "failed", "reason": str(e)}


class RegistrationHandler(EventHandler):
    """Handles trader registration events."""
    
    def __init__(self, trader_service: TraderService):
        self.trader_service = trader_service
    
    async def handle(self, event: TraderRegisteredEvent) -> Optional[Dict[str, Any]]:
        """Handle trader registration."""
        return await self.trader_service.register_trader(
            event.trader_id,
            event.trader_type,
            event.gmail_username,
            event.trader_instance
        )


class InventoryHandler(EventHandler):
    """Handles inventory report events."""
    
    def __init__(self, trader_service: TraderService, pricing_service: PricingService,
                 order_service: OrderService, transaction_service: TransactionService,
                 market_id: str):
        self.trader_service = trader_service
        self.pricing_service = pricing_service
        self.order_service = order_service
        self.transaction_service = transaction_service
        self.market_id = market_id
    
    async def handle(self, event: InventoryReportEvent) -> Optional[Dict[str, Any]]:
        """Handle inventory report."""
        # Process inventory through trader service
        closure_orders = await self.trader_service.process_inventory_report(
            event.trader_id, event.shares, self.pricing_service
        )
        
        # Process closure orders
        for trader_order, platform_order, closure_price in closure_orders:
            # Set market IDs
            trader_order.market_id = self.market_id
            platform_order.market_id = self.market_id
            platform_order.trader_id = self.market_id  # Platform acts as counterparty
            
            # Place both orders
            await self.order_service.process_order(platform_order.model_dump())
            await self.order_service.process_order(trader_order.model_dump())
            
            # Create transaction
            if trader_order.order_type == OrderType.BID:
                await self.transaction_service.create_transaction(
                    trader_order.model_dump(),
                    platform_order.model_dump(),
                    closure_price,
                )
            else:
                await self.transaction_service.create_transaction(
                    platform_order.model_dump(),
                    trader_order.model_dump(),
                    closure_price,
                )
        
        return {}


class StatusHandler(EventHandler):
    """Handles trader status update events."""
    
    def __init__(self, broadcast_service):
        self.broadcast_service = broadcast_service
    
    async def handle(self, event) -> Optional[Dict[str, Any]]:
        """Handle trader status update."""
        
        # Determine parameter name based on trader type
        trader_type = getattr(event, 'trader_type', 'noise')
        param_name = f"{trader_type}_trader_status"
        
        # Broadcast status update to all clients
        await self.broadcast_service.broadcast_to_websockets({
            "type": "trader_status_update",
            "trader_id": event.trader_id,
            "trader_status": event.trader_status,
            "trader_type": trader_type,
            "param_name": param_name,
        })
        
        return {"status": "broadcast_sent"}


class LoggingMiddleware:
    """Middleware for logging all events."""
    
    def __init__(self, trading_logger):
        self.trading_logger = trading_logger
    
    async def __call__(self, event: TradingEvent) -> TradingEvent:
        """Log event details."""
        # Log basic event info (can be extended)
        logger.debug(f"Processing event: {type(event).__name__} - {event.id}")
        return event


class MarketOrchestrator:
    """Orchestrates the entire market using event-driven architecture."""
    
    def __init__(self, market_id: str, duration: int, default_price: int,
                 default_spread: int, punishing_constant: int, params: Dict):
        self.market_id = market_id
        self.duration = duration
        self.params = params
        
        # Core components (same as before)
        from .orderbook_manager import OrderBookManager
        from .transaction_manager import TransactionManager
        from utils.utils import setup_trading_logger
        
        self.order_book_manager = OrderBookManager()
        self.transaction_manager = TransactionManager(market_id)
        self.trading_logger = setup_trading_logger(market_id)
        self.order_lock = asyncio.Lock()
        
        # Services
        self.pricing_service = PricingService(default_price, default_spread, punishing_constant)
        self.order_service = OrderService(self.order_book_manager, self.pricing_service)
        self.transaction_service = TransactionService(self.transaction_manager)
        self.trader_service = TraderService()
        self.broadcast_service = BroadcastService(
            self.order_book_manager, self.transaction_manager, self.pricing_service
        )
        
        # Connect services
        self.broadcast_service.set_trader_registry(self.trader_service.connected_traders)
        self.broadcast_service._market_id = market_id
        
        # Event system
        from .events import MessageBus, MessageRouter
        self.message_bus = MessageBus()
        self.message_router = MessageRouter(self.message_bus)
        
        # State
        self.active = False
        self.start_time: Optional[datetime] = None
        self.creation_time = datetime.now()
        self.initialization_complete = False
        self.trading_started = False
        self.is_finished = False
        self._stop_requested = asyncio.Event()
        self.process_transactions_task = None
        
        self._setup_event_handlers()
    
    def _setup_event_handlers(self):
        """Set up event handlers."""
        # Create handlers
        order_handler = OrderHandler(
            self.order_service, self.transaction_service, self.broadcast_service,
            self.trading_logger, self.order_lock, self.market_id, lambda: self.active
        )
        
        cancel_handler = CancelHandler(
            self.order_service, self.broadcast_service, self.trading_logger,
            lambda: self.active
        )
        
        registration_handler = RegistrationHandler(self.trader_service)
        
        inventory_handler = InventoryHandler(
            self.trader_service, self.pricing_service, self.order_service,
            self.transaction_service, self.market_id
        )
        
        status_handler = StatusHandler(self.broadcast_service)
        
        # Subscribe handlers to events
        from .events import OrderPlacedEvent, OrderCancelledEvent, TraderRegisteredEvent, InventoryReportEvent, StatusUpdateEvent
        self.message_bus.subscribe(OrderPlacedEvent, order_handler)
        self.message_bus.subscribe(OrderCancelledEvent, cancel_handler)
        self.message_bus.subscribe(TraderRegisteredEvent, registration_handler)
        self.message_bus.subscribe(InventoryReportEvent, inventory_handler)
        self.message_bus.subscribe(StatusUpdateEvent, status_handler)
        
        # Add logging middleware
        self.message_bus.add_middleware(LoggingMiddleware(self.trading_logger))
    
    # Public interface (same as original TradingPlatform)
    async def handle_trader_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Main entry point - route messages to event system."""
        return await self.message_router.route_message(message)
    
    def register_websocket(self, websocket):
        """Register WebSocket connection."""
        self.broadcast_service.register_websocket(websocket)
    
    def unregister_websocket(self, websocket):
        """Unregister WebSocket connection."""
        self.broadcast_service.unregister_websocket(websocket)
    