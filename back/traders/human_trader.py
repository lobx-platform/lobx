from .base_trader import BaseTrader, PausingTrader
from starlette.websockets import WebSocketDisconnect, WebSocketState
import random
import json

from core.data_models import TraderType, OrderType
from utils import setup_custom_logger
import traceback

logger = setup_custom_logger(__name__)

class HumanTrader(PausingTrader):

    def __init__(self, id, cash=0, shares=0, goal=0, role=None, trading_market=None, params=None, gmail_username=None):
        super().__init__(TraderType.HUMAN, id, cash, shares)
        self.goal = goal
        self.role = role
        self.trading_market = trading_market
        self.params = params
        self.gmail_username = gmail_username
        self.websocket = None
        self.goal_progress = 0

        # Socket.IO fields (used when connected via Socket.IO instead of raw WS)
        self._sio = None        # socketio.AsyncServer instance
        self._sio_sid = None    # Socket.IO session id
        self._sio_room = None   # market room id

    def get_trader_params_as_dict(self):
        return {
            "id": self.id,
            "type": self.trader_type,
            "initial_cash": self.initial_cash,
            "initial_shares": self.initial_shares,
            "goal": self.goal,
            "goal_progress": self.goal_progress,  # Add this line
            **self.params
        }

    async def on_message_from_system(self, data):
        """Handle messages from the trading platform and send individual trader data."""
        # Call parent class to handle the basic message processing
        await super().on_message_from_system(data)
        
        # Check and send human trader pause status
        await self.update_human_pause_status()
        
        # Always send updated individual trader data to the frontend
        # This ensures PnL, shares, cash calculations are sent in real-time
        await self.send_message_to_client("BOOK_UPDATED")

    async def post_processing_server_message(self, json_message):
        # Use .get() instead of .pop() to avoid mutating the shared message dict
        # that is sent to multiple traders
        message_type = json_message.get("type", None)
        if message_type:
            # Create a copy without 'type' for kwargs
            message_data = {k: v for k, v in json_message.items() if k != "type"}
            await self.send_message_to_client(message_type, **message_data)

    async def connect_to_socketio(self, sio, sid, market_id):
        """Connect this trader via Socket.IO instead of raw WebSocket."""
        try:
            self._sio = sio
            self._sio_sid = sid
            self._sio_room = market_id
            self.socket_status = True

            await self.initialize()
            await self.connect_to_market(self.trading_market.id, self.trading_market)

            # Register with the trading platform directly
            await self.trading_market.handle_register_me({
                "trader_id": self.id,
                "trader_type": self.trader_type,
                "gmail_username": self.gmail_username,
                "trader_instance": self,
            })
        except Exception as e:
            traceback.print_exc()

    async def connect_to_socket(self, websocket):
        try:
            self.websocket = websocket
            self.socket_status = True

            await self.initialize()
            await self.connect_to_market(self.trading_market.id, self.trading_market)

            # Register WebSocket with the trading platform for broadcasting
            self.trading_market.register_websocket(websocket)

            # Register with the trading platform directly
            await self.trading_market.handle_register_me({
                "trader_id": self.id,
                "trader_type": self.trader_type,
                "gmail_username": self.gmail_username,
                "trader_instance": self
            })
        except Exception as e:
            traceback.print_exc()

    async def send_message_to_client(self, message_type, **kwargs):
        if not self.socket_status:
            return

        # Check that we have at least one transport
        has_ws = self.websocket and self.websocket.client_state == WebSocketState.CONNECTED
        has_sio = self._sio is not None and self._sio_sid is not None

        if not has_ws and not has_sio:
            return

        order_book = self.order_book or {"bids": [], "asks": []}
        kwargs["trader_orders"] = self.orders
        try:
            message = {
                "shares": self.shares,
                "cash": self.cash,
                "pnl": self.get_current_pnl(),
                "type": message_type,
                "inventory": dict(shares=self.shares, cash=self.cash),
                "goal": self.goal,
                "goal_progress": self.goal_progress,
                **kwargs,
                "order_book": order_book,
                "initial_cash": self.initial_cash,
                "initial_shares": self.initial_shares,
                "sum_dinv": self.sum_dinv,
                "vwap": self.get_vwap(),
                "filled_orders": self.filled_orders,
                "placed_orders": self.placed_orders,
            }
            from utils.websocket_utils import sanitize_websocket_message
            sanitized_message = sanitize_websocket_message(message)

            # Socket.IO path
            if has_sio:
                event = message_type.lower()  # e.g. "BOOK_UPDATED" -> "book_updated"
                await self._sio.emit(event, sanitized_message, to=self._sio_sid)
            # Legacy raw WebSocket path
            elif has_ws:
                await self.websocket.send_json(sanitized_message)
        except WebSocketDisconnect:
            self.socket_status = False
            if hasattr(self, 'trading_market') and self.trading_market:
                self.trading_market.unregister_websocket(self.websocket)
        except Exception as e:
            traceback.print_exc()

    async def on_message_from_client(self, message):
        try:
            json_message = json.loads(message)
            action_type = json_message.get("type")
            data = json_message.get("data")
            handler = getattr(self, f"handle_{action_type}", None)
            if handler:
                await handler(data)
            else:
                logger.critical(
                    f"Do not recognice the type: {action_type}. Invalid message format: {message}"
                )
        except json.JSONDecodeError:
            logger.critical(f"Error decoding message: {message}")

    async def update_human_pause_status(self):
        """Update human trader pause status based on algo sleep state."""
        # Only send status updates if sleep parameters are configured
        if (hasattr(self, 'sleep_duration') and self.sleep_duration > 0 and 
            hasattr(self, 'should_human_be_paused')):
            is_paused = self.should_human_be_paused()
            status = "paused" if is_paused else "active"
            
            if hasattr(self, 'trading_market') and self.trading_market:
                await self.trading_market.handle_trader_message({
                    "action": "status_update",
                    "trader_id": self.id,
                    "trader_status": status,
                    "trader_type": "human",
                    "is_status_update": True
                })

    async def handle_add_order(self, data):
        # Only check pause status if sleep parameters are configured
        if (hasattr(self, 'sleep_duration') and self.sleep_duration > 0 and 
            hasattr(self, 'should_human_be_paused') and self.should_human_be_paused()):
            logger.info(f"Human trader {self.id} order blocked - algos are active")
            return
            
        order_type = data.get("type")
        price = data.get("price")
        amount = data.get("amount", 1)
        
        logger.info(f"Human trader {self.id} placing order: {order_type} {amount}@{price}")
        await self.post_new_order(amount, price, order_type)

    async def handle_cancel_order(self, data):
        order_uuid = data.get("id")

        if order_uuid in [order["id"] for order in self.orders]:
            await self.send_cancel_order_request(order_uuid)

    async def handle_closure(self, data):
        await self.post_processing_server_message(data)
        await super().handle_closure(data)

    async def clean_up(self):
        """Override base cleanup to also unregister websocket / Socket.IO."""
        await super().clean_up()
        # Unregister raw websocket from trading platform
        if hasattr(self, 'trading_market') and self.trading_market and hasattr(self, 'websocket') and self.websocket:
            self.trading_market.unregister_websocket(self.websocket)
        # Clear Socket.IO references
        self._sio = None
        self._sio_sid = None
        self._sio_room = None

    async def handle_TRADING_STARTED(self, data):
        """
        Handle the TRADING_STARTED message by placing a zero-amount order.
        This ensures that human traders who don't trade still generate records.
        """
        # Get the current market price
        top_bid = None
        top_ask = None
        
        if self.order_book:
            bids = self.order_book.get("bids", [])
            asks = self.order_book.get("asks", [])
            
            if bids:
                top_bid = max(bid["x"] for bid in bids)
            if asks:
                top_ask = min(ask["x"] for ask in asks)
        
        # Use default price if order book is empty
        price = self.params.get("default_price", 100)
        if top_bid and top_ask:
            price = (top_bid + top_ask) // 2
        elif top_bid:
            price = top_bid
        elif top_ask:
            price = top_ask
            
        # Place a zero-amount order (this will be recorded but won't affect the market)
        # Use BID order type by default
        order_type = OrderType.BID
        await self.post_new_order(0, price, order_type)
        
        # Forward the message to the client
        await self.post_processing_server_message(data)
