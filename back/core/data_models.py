import asyncio
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from enum import Enum, IntEnum
from typing import Optional, List, Dict
from uuid import UUID, uuid4
import random
from pydantic import BaseModel, ConfigDict, Field, field_validator

# basic enums
class StrEnum(str, Enum):
    pass

class TradeDirection(str, Enum):
    BUY = "buy" 
    SELL = "sell"

# user stuff
class User(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    username: str
    is_admin: bool = False

class Trader(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    gmail_username: str  # gmail username for auth
    trading_market_id: UUID
    is_ready: bool = False  # tracks if user hit start

class TradingPlatform(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    status: str = "waiting"
    traders: List[UUID] = []

class UserRegistration(BaseModel):
    username: str
    password: str

# trader types
class TraderType(str, Enum):
    NOISE = "NOISE"
    MARKET_MAKER = "MARKET_MAKER"
    INFORMED = "INFORMED"
    HUMAN = "HUMAN"
    INITIAL_ORDER_BOOK = "INITIAL_ORDER_BOOK"


class ThrottleConfig(BaseModel):
    order_throttle_ms: int = 0  # 0 means no throttling
    max_orders_per_window: int = 1  # Only used if throttle_ms > 0


# all the trading params - lots of them!
class TradingParameters(BaseModel):
    # basic setup
    num_noise_traders: int = Field(
        default=1,
        title="Number of Noise Traders", 
        description="model_parameter",
        ge=0,
    )
    num_informed_traders: int = Field(
        default=1,
        title="Number of Informed Traders",
        description="model_parameter", 
        ge=0,
    )
    # book setup
    start_of_book_num_order_per_level: int = Field(
        default=3,
        title="Orders per Level at Book Start",
        description="model_parameter",
        ge=0,
    )
    trading_day_duration: float = Field(
        default=3,
        title="Trading Day Duration (minutes)",
        description="model_parameter",
        gt=0,
    )
    step: int = Field(
        default=1,
        title="Step for New Orders",
        description="model_parameter",
    )
    depth_weights: List[int] = Field(
        default=[1,1,1,1,1],
        title="Depth Weights",
        description="model_parameter",
    )

    # noise trader settings
    noise_activity_frequency: float = Field(
        default=1,
        title="Activity Frequency",
        description="noise_parameter",
        gt=0,
    )
    max_order_amount: int = Field(
        default=1,
        title="Order Amount",
        description="noise_parameter",
    )
    noise_passive_probability: float = Field(
        default=0.8,
        title="Passive Order Probability",
        description="noise_parameter",
    )
    noise_cancel_probability: float = Field(
        default=0.6,
        title="Cancel Order Probability",
        description="noise_parameter",
    )
    noise_bid_probability: float = Field(
        default=0.5,
        title="Bid Order Probability",
        description="noise_parameter",
    )
    sleep_duration: float = Field(
        default=0,
        title="Sleep Duration (seconds)",
        description="noise_parameter",
        ge=0,
    )
    sleep_interval: float = Field(
        default=60,
        title="Sleep Interval (seconds)",
        description="noise_parameter",
        gt=0,
    )
    noise_pr_passive_weights: List[int] = Field(
        default=[40,20,10,5,5,5,5,5,5,0],
        title="Passive Odds/Ratios",
        description="noise_parameter",
    )
    noise_alpha: float = Field(
        default=0.33,
        title="Mid-Price Smoothing Alpha",
        description="noise_parameter",
        gt=0,
        le=1,
    )
    noise_bias_thresh: float = Field(
        default=3,
        title="Bid Probability Bias Threshold",
        description="noise_parameter",
        ge=0,
    )

    # informed trader settings
    informed_trade_intensity: float = Field(
        default=0.69,
        title="Trade Intensity",
        description="informed_parameter",
    )
    informed_trade_direction: TradeDirection = Field(
        default=TradeDirection.BUY,
        title="Trade Direction",
        description="informed_parameter",
    )
    informed_edge: int = Field(
        default=3,
        title="Informed Edge",
        description="informed_parameter",
    )
    informed_order_book_levels: int = Field(
        default=1,
        title="Informed Order Book Levels",
        description="informed_parameter",
    )
    informed_order_book_cancel: int = Field(
        default=2,
        title="Informed Order Book Cancel",
        description="informed_parameter",
    )
    informed_use_passive_orders: bool = Field(
        default=False,
        title="Use Passive Orders",
        description="informed_parameter",
    )
    informed_random_direction: bool = Field(
        default=True,
        title="Randomly Flip Trade Direction",
        description="informed_parameter",
    )
    informed_share_passive: float = Field(
        default=0.1,
        title="Share passive orders",
        description="informed_parameter",
    )

    # human trader settings
    initial_cash: float = Field(
        default=1200,
        title="Initial Cash",
        description="human_parameter",
    )
    initial_stocks: int = Field(
        default=10,
        title="Initial Stocks",
        description="human_parameter",
    )

    # general market settings
    order_book_levels: int = Field(
        default=30,
        title="Order Book Levels",
        description="model_parameter",
    )
    default_price: int = Field(
        default=100,
        title="Default Price",
        description="model_parameter",
    )

    conversion_rate: float = Field(
        default=1,
        title="Lira-GBP Conversion Rate",
        description="model_parameter",
        gt=0,
    )

    max_markets_per_human: int = Field(
        default=6,
        title="Max Markets per Human",
        description="human_parameter",
        ge=1,
    )
    
    market_sizes: List[int] = Field(
        default=[],
        title="Market Sizes (Cohorts)",
        description="human_parameter",
    )

    # session type (prolific or lab)
    session_type: str = Field(
        default="prolific",
        title="Session Type",
        description="human_parameter",
    )

    # admin stuff
    google_form_id: str = Field(
        default='1yDf7vd5wLaPhm30IiGKTkPw4s5spb3Xlm86Li81YDXI',
        title="Google Form ID",
        description="model_parameter",
    )

    # goal settings
    predefined_goals: List[int] = Field(
        default=[0],
        title="Predefined Goals",
        description="human_parameter",
    )

    allow_random_goals: bool = Field(
        default=True,
        title="Allow Random Goal Assignment",
        description="human_parameter",
    )

    throttle_settings: Dict[TraderType, ThrottleConfig] = Field(
        default_factory=lambda: {
            TraderType.HUMAN: ThrottleConfig(order_throttle_ms=100, max_orders_per_window=1),
            TraderType.NOISE: ThrottleConfig(),
            TraderType.INFORMED: ThrottleConfig(),
            TraderType.MARKET_MAKER: ThrottleConfig(),
            TraderType.INITIAL_ORDER_BOOK: ThrottleConfig(),
        },
        title="Throttle Settings Per Trader Type",
        description="model_parameter"
    )

    @field_validator('predefined_goals', mode='before')
    def validate_predefined_goals(cls, v):
        if isinstance(v, str):
            try:
                # Convert string to list of integers
                goals = [int(x.strip()) for x in v.split(',')]
                # Don't override with default if empty
                return goals
            except ValueError:
                raise ValueError("Predefined goals must be comma-separated numbers!")
        elif isinstance(v, list):
            # Convert list items to integers but don't set default
            goals = [int(x) for x in v]
            return goals
        else:
            raise ValueError("Predefined goals must be comma-separated string or number list!")
    
    @field_validator('market_sizes', mode='before')
    def validate_market_sizes(cls, v):
        if isinstance(v, str):
            if not v.strip():
                return []
            try:
                sizes = [int(x.strip()) for x in v.split(',') if x.strip()]
                return sizes
            except ValueError:
                raise ValueError("Market sizes must be comma-separated numbers!")
        elif isinstance(v, list):
            if not v:
                return []
            sizes = [int(x) for x in v]
            return sizes
        else:
            return []

    def dump_params_by_description(self) -> dict:
        """organize params by their type"""
        result = {}
        for field_name, field_info in self.model_fields.items():
            description = field_info.description
            if description not in result:
                result[description] = {}
            result[description][field_name] = getattr(self, field_name)
        return result

    def update(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    @classmethod
    def create_with_base_settings(cls, base_params: dict, base_settings: dict):
        merged_params = {**base_params, **base_settings}
        # need 2+ humans
        merged_params['num_human_traders'] = max(merged_params.get('num_human_traders', 2), 2)
        return cls(**merged_params)

    @classmethod
    def from_dict(cls, data: dict):
        converted_data = {}
        for field, value in data.items():
            if field in cls.model_fields:
                field_info = cls.model_fields[field]
                try:
                    if isinstance(value, str):
                        if field_info.annotation == int:
                            converted_data[field] = int(value)
                        elif field_info.annotation == float:
                            converted_data[field] = float(value)
                        elif field_info.annotation == bool:
                            converted_data[field] = value.lower() in ('true', '1', 'yes')
                        elif field_info.annotation == List[int]:
                            converted_data[field] = [int(v.strip()) for v in value.split(',')]
                        else:
                            converted_data[field] = value
                    else:
                        converted_data[field] = value
                except ValueError as e:
                    print(f"oops, error converting {field}: {str(e)}")
                    converted_data[field] = value
        return cls(**converted_data)


# lobster data stuff
class LobsterEventType(IntEnum):
    """maps lobster event types to numbers"""
    NEW_LIMIT_ORDER = 1
    CANCELLATION_PARTIAL = 2
    CANCELLATION_TOTAL = 3
    EXECUTION_VISIBLE = 4
    EXECUTION_HIDDEN = 5
    CROSS_TRADE = 6
    TRADING_HALT = 7


# action types
class ActionType(str, Enum):
    POST_NEW_ORDER = "add_order"
    CANCEL_ORDER = "cancel_order"
    UPDATE_BOOK_STATUS = "update_book_status"
    REGISTER = "register_me"


# order stuff
class OrderType(IntEnum):
    ASK = -1  # selling price
    BID = 1   # buying price

str_to_order_type = {"ask": OrderType.ASK, "bid": OrderType.BID}

class OrderStatus(str, Enum):
    BUFFERED = "buffered"
    ACTIVE = "active"
    EXECUTED = "executed"
    CANCELLED = "cancelled"


# order model
class Order(BaseModel):
    id: Optional[str] = None
    status: OrderStatus
    amount: float = 1
    price: float
    order_type: OrderType
    timestamp: datetime = Field(default_factory=datetime.now)
    market_id: str
    trader_id: str  # gmail username
    informed_trader_progress: Optional[str] = None

    class ConfigDict:
        use_enum_values = True

executor = ThreadPoolExecutor()

# transaction stuff
class TransactionModel:
    def __init__(self, trading_market_id, bid_order_id, ask_order_id, price, informed_trader_progress=None):
        self.id = uuid.uuid4()
        self.trading_market_id = trading_market_id
        self.bid_order_id = bid_order_id
        self.ask_order_id = ask_order_id
        self.timestamp = datetime.now(timezone.utc)
        self.price = price
        self.informed_trader_progress = informed_trader_progress

    def to_dict(self):
        return {
            "id": str(self.id),
            "trading_market_id": self.trading_market_id,
            "bid_order_id": self.bid_order_id,
            "ask_order_id": self.ask_order_id,
            "timestamp": self.timestamp.isoformat(),
            "price": self.price,
            "informed_trader_progress": self.informed_trader_progress
        }

# message model
class Message:
    def __init__(self, trading_market_id: str, content: Dict, message_type: str = "BOOK_UPDATED"):
        self.id: UUID = uuid4()
        self.trading_market_id: str = trading_market_id
        self.content: Dict = content
        self.timestamp: datetime = datetime.now(timezone.utc)
        self.type: str = message_type

    def to_dict(self) -> Dict:
        return {
            "id": str(self.id),
            "trading_market_id": self.trading_market_id,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "type": self.type
        }

class TraderRole(str, Enum):
    INFORMED = "informed"
    SPECULATOR = "speculator"
