import asyncio
import random
import traceback
from typing import List, Dict, Union
from datetime import datetime

from core.data_models import OrderType, TraderType, TradeDirection
from .base_trader import BaseTrader, PausingTrader


class InformedTrader(PausingTrader):
    def __init__(
        self,
        id: str,
        params: dict,
    ):
        super().__init__(trader_type=TraderType.INFORMED, id=id)
        self.default_price = params.get("default_price", 100)
        self.informed_edge = params.get("informed_edge", 2)
        self.params = params
        self.informed_order_book_levels = params.get("informed_order_book_levels", 3)
        self.informed_order_book_cancel = params.get("informed_order_book_cancel", 3)
        self.use_passive_orders = params.get("informed_use_passive_orders", False)
        # Order multiplier to increase trading volume
        self.order_multiplier = 1
        
        # Add random direction handling
        if params.get("informed_random_direction", False):
             # Randomly flip the direction with 50% probability
            if random.random() < 0.5:
                self.params["informed_trade_direction"] = (
                    TradeDirection.SELL 
                    if params["informed_trade_direction"] == TradeDirection.BUY 
                    else TradeDirection.BUY
                )
            
        self.goal = self.initialize_inventory(params)
        self.num_passive_to_keep = int(self.params["informed_share_passive"] * self.goal * self.order_multiplier)
        # Adjust sleep time to account for increased order volume
        self.next_sleep_time = params.get("trading_day_duration", 5) * 60 / (self.goal * self.order_multiplier)
        self.shares_traded = 0
        
        # Initialize outstanding_levels dictionary to track orders at different price levels
        self.outstanding_levels = {}

    @property
    def progress(self) -> float:
        if not self.filled_orders:
            return 0
        filled_amount = sum(order["amount"] for order in self.filled_orders)
        return filled_amount / (self.goal * self.order_multiplier) if self.goal > 0 else 1

    @property
    def target_progress(self) -> float:
        return self.get_elapsed_time() / (self.params["trading_day_duration"] * 60)

    @property
    def order_placement_levels(self) -> list:
        trade_direction = self.params["informed_trade_direction"]
        order_side = (
            OrderType.BID if trade_direction == TradeDirection.BUY else OrderType.ASK
        )

        top_bid = self.get_best_price(OrderType.BID)
        top_ask = self.get_best_price(OrderType.ASK)
        
        # Return empty list if either price is None
        if top_bid is None or top_ask is None:
            return []

        mid_price = int((top_bid + top_ask) / 2)

        levels = []
        if order_side == OrderType.BID:
            for i in range(self.informed_order_book_levels):
                level_price = top_bid - (i * self.params["step"])
                if level_price > 0:  # Ensure price is positive
                    levels.append(level_price)
        else:  # OrderType.ASK
            for i in range(self.informed_order_book_levels):
                level_price = top_ask + (i * self.params["step"])
                levels.append(level_price)

        return levels

    def initialize_inventory(self, params: dict) -> int:
        expected_noise_amount_per_action = (1 + params["max_order_amount"]) / 2
        expected_noise_number_of_actions = (
            params["trading_day_duration"] * 60 * params["noise_activity_frequency"]
        )
        expected_noise_volume = (
            expected_noise_amount_per_action
            * expected_noise_number_of_actions
            * (1 - params["noise_passive_probability"])
        )
        x = params["informed_trade_intensity"]

        goal = int((x / (1 - x)) * expected_noise_volume)

        if params["informed_trade_direction"] == TradeDirection.BUY:
            self.shares = 0
            self.cash = goal * params["default_price"] * 2
        else:
            self.shares = goal
            self.cash = 0

        return goal

    async def cancel_all_outstanding_orders(self):
        """Cancel all outstanding orders."""
        if hasattr(self, 'outstanding_levels') and self.outstanding_levels:
            for orders in self.outstanding_levels.values():
                await self.cancel_order(orders["order_ids"])

    def get_remaining_time(self) -> float:
        return self.params["trading_day_duration"] * 60 - self.get_elapsed_time()


    async def cancel_order(self, order_ids: Union[str, List[str]]) -> None:
        if isinstance(order_ids, str):
            order_ids = [order_ids]

        for order_id in order_ids:
            await self.send_cancel_order_request(order_id)

    def get_best_price(self, order_side: OrderType) -> float:
        if order_side == OrderType.BID:
            bids = self.order_book.get("bids", [])
            return max(bid["x"] for bid in bids) if bids else None
        else:  # OrderType.ASK
            asks = self.order_book.get("asks", [])
            return min(ask["x"] for ask in asks) if asks else None

    def calculate_spread(self,top_bid_price, top_ask_price):
        if top_bid_price is None or top_ask_price is None:
            spread = float('Inf')
        else:
            spread = top_ask_price - top_bid_price
            
        return spread

    def calculate_sleep_time(self,remaining_time,number_trades,goal):
        if goal <= number_trades:
            sleep_time = 1000
        else:
            sleep_time = max(0.5,(remaining_time - 7) / (goal - number_trades))
        return sleep_time


    async def _place_passive_orders(self, amt: int, side: str) -> None:
        amt = int(amt)
        order_book_levels = self.informed_order_book_levels
        step = self.params["step"]
        default_price = self.params["default_price"]
        
        anchor = default_price
        if side == "bids":
            if self.order_book["asks"]:
                best_ask = self.order_book["asks"][0]["x"]
                anchor = best_ask
            sign = -1
            order_type = OrderType.BID
        else:    
            if self.order_book["bids"]:
                best_bid = self.order_book["bids"][0]["x"]
                anchor = best_bid
            sign = 1  
            order_type = OrderType.ASK
        
        for iter in range(amt):
            levels = random.randint(1, order_book_levels) * step
            price = anchor + sign*levels
            await self.post_new_order(1, price, order_type)
    
    async def _place_tightening_passive_orders(self, amt: int, side: str, spread_ticks: int) -> None:
        
        amt = int(amt)
        order_book_levels = self.informed_order_book_levels
        step = self.params["step"]
        default_price = self.params["default_price"]
        anchor = default_price
        
        
        if side == "bids":
            if self.order_book["bids"]:
                best_bid = self.order_book["bids"][0]["x"]
                anchor = best_bid
            sign = 1
            order_type = OrderType.BID
        else:    
            if self.order_book["asks"]:
                best_ask = self.order_book["asks"][0]["x"]
                anchor = best_ask
            sign = -1  
            order_type = OrderType.ASK
        half_spread_ticks = int(spread_ticks/2) 
        # Maximum depth allowed: no crossing + informed level limit
        max_levels = max(1,min(half_spread_ticks, self.informed_order_book_levels))
        # Randomly choose how many consecutive levels to fill
        level = random.randint(1, max_levels)
    
        # Remaining budget to allocate
        remaining_amt = amt
        # Fill all intermediate levels with random shares
        for k in range(1, level + 1):
            # Stop if fully allocated
            if remaining_amt == 0:
                break
            # Random share of what remains
            size = random.randint(1, remaining_amt)
            # Price at this level
            price = anchor + sign * k * step
            # Post the passive order
            for _ in range(size):
                await self.post_new_order(1, price, order_type)
            # Reduce remaining budget
            remaining_amt -= size
    
    async def _manage_passive_orders(self):
        trade_direction = self.params["informed_trade_direction"]
        order_side = OrderType.BID if trade_direction == TradeDirection.BUY else OrderType.ASK
        step = self.params["step"]
        self.number_trades = sum(fill["amount"] for fill in self.filled_orders)
        # print('total goal', self.goal)
        #print('number of trades', self.number_trades)
    
        # Get order placement levels
        #levels = self.order_placement_levels
        #print('order placement levels:',levels)
      
        ###################################
        # step one: cancel orders that
        # are in level>=self.informed_order_book_cancel (equality because levels start from 0)
    
        if order_side == OrderType.BID:
            top_bid_price = self.get_best_price(OrderType.BID)
            for order in self.orders:
                levels_from_best = int((top_bid_price - order['price'])/step)
                if levels_from_best >=self.informed_order_book_cancel:
                    order_id = order['id']
                    await self.send_cancel_order_request(order_id)
      
        else:
            top_ask_price = self.get_best_price(OrderType.ASK)
            for order in self.orders:
                levels_from_best = int((order['price'] - top_ask_price)/step)
                if levels_from_best >= self.informed_order_book_cancel:
                    order_id = order['id']
                    await self.send_cancel_order_request(order_id)
    
        ###################################
        # step two: cancel orders if 
        # remaining_trades to achieve goal
        # are less than or equal to the number of passive orders at the top levels
        remaining_trades = max(self.goal - self.number_trades,0)
        total_passive_are_all_levels =  sum(order['amount'] for order in self.orders)   
    
        if remaining_trades <= total_passive_are_all_levels:
            num_orders_to_cancel_raw = int(total_passive_are_all_levels - remaining_trades+1)
            num_orders_to_cancel     = int(min(num_orders_to_cancel_raw ,total_passive_are_all_levels))
            if order_side == OrderType.BID:
                sorted_orders = sorted(self.orders,
                      key=lambda x: (
                          x["price"],-datetime.strptime(x["timestamp"], "%Y-%m-%d %H:%M:%S.%f").timestamp()))
                orders_to_cancel = sorted_orders[:num_orders_to_cancel]
                for order in orders_to_cancel:
                    order_id = order['id']
                    await self.send_cancel_order_request(order_id)
            else:
                sorted_orders = sorted(self.orders,
                      key=lambda x: (
                          -x["price"],-datetime.strptime(x["timestamp"], "%Y-%m-%d %H:%M:%S.%f").timestamp()))
                orders_to_cancel = sorted_orders[:num_orders_to_cancel]
                for order in orders_to_cancel:
                    order_id = order['id']
                    await self.send_cancel_order_request(order_id)
            return
      
        # calculate how many passive orders i need to send
        # the number of passive orders should belong to
        # informed_order_book_levels
    
        #this calculates how many passive orders already exist 
        #on top levels
        if order_side == OrderType.BID:
            top_bid_price = self.get_best_price(OrderType.BID)
            prices_to_check = [top_bid_price - i*step for i in range(self.informed_order_book_levels)]
            self.total_number_passive_orders = sum(order['price'] in prices_to_check for order in self.orders)
        else:
            top_ask_price = self.get_best_price(OrderType.ASK)
            prices_to_check = [top_ask_price + i*step for i in range(self.informed_order_book_levels)]
            self.total_number_passive_orders = sum(order['price'] in prices_to_check for order in self.orders)
    
    
        #print('number of passive orders exist:', self.total_number_passive_orders)
    

        if self.total_number_passive_orders < self.num_passive_to_keep:
            remaining_trades = max(self.goal - self.number_trades,0)
            if remaining_trades >= self.num_passive_to_keep:
                num_passive_order_to_send = self.num_passive_to_keep - self.total_number_passive_orders
            else:
                num_passive_order_to_send = max(remaining_trades -  self.total_number_passive_orders,0)
        else:
            num_passive_order_to_send = 0
    
        #print('num_passive_order_to_send',num_passive_order_to_send)
        # send passive orders at the top self.informed_order_book_levels levels
        if int(num_passive_order_to_send) > 0:
            # last send aggresive order if needed
            top_bid_price = self.get_best_price(OrderType.BID)
            top_ask_price = self.get_best_price(OrderType.ASK)
        
            spread = self.calculate_spread(top_bid_price, top_ask_price)
            spread_ticks = int(spread /step)
            amt = int(num_passive_order_to_send)
            side = "bids" if trade_direction == TradeDirection.BUY else "asks"  
            if spread >= self.informed_edge:#tighten spread
                await self._place_tightening_passive_orders(amt, side, spread_ticks)
            else:
                await self._place_passive_orders(amt, side)
        

    async def check(self) -> None:
        remaining_time = self.get_remaining_time()
        self.number_trades = sum(fill["amount"] for fill in self.filled_orders)
           
        if remaining_time < 2 or (abs(self.goal * self.order_multiplier - self.number_trades) <= 0):
            #print(f'Informed trader fullfilled goal with {self.number_trades} trades')
            return
    
        trade_direction = self.params["informed_trade_direction"]
        order_side = OrderType.BID if trade_direction == TradeDirection.BUY else OrderType.ASK
    
        top_bid_price = self.get_best_price(OrderType.BID)
        top_ask_price = self.get_best_price(OrderType.ASK)
           
        if top_bid_price is None and top_ask_price is None:
            return
       
        spread = self.calculate_spread(top_bid_price, top_ask_price)
        spread_ticks = int(spread / self.params["step"])
           
        if self.use_passive_orders:
            # Manage passive orders if enabled
            await self._manage_passive_orders()
           
        #I think this is executed trades
        self.number_trades = sum(fill["amount"] for fill in self.filled_orders)

        cond_aggressive = ( (self.number_trades < (self.goal * self.order_multiplier)) and (spread_ticks < self.informed_edge))

        top_bid_price = self.get_best_price(OrderType.BID)
        top_ask_price = self.get_best_price(OrderType.ASK)

        if cond_aggressive:
            cond_buy = (order_side == OrderType.BID) and (top_ask_price is not None)
            cond_sell = (order_side == OrderType.ASK) and (top_bid_price is not None)
                           
            # aggressive-only behavior
            if cond_buy:
                price_to_send = top_ask_price
                # Increase order amount by multiplier
                amount = self.order_multiplier
            elif cond_sell:
                   price_to_send = top_bid_price
                   # Increase order amount by multiplier
                   amount = self.order_multiplier
            else:
                return
            
            #place the order    
            await self.post_new_order(amount, price_to_send, order_side)
           
        #cancel any outstanding order if the goal is reached
        self.number_trades = sum(fill["amount"] for fill in self.filled_orders)
        if self.number_trades >= (self.goal * self.order_multiplier):
            for order in self.orders:
                order_id = order['id']
                await self.send_cancel_order_request(order_id)
         
           
        self.number_trades = sum(fill["amount"] for fill in self.filled_orders)
        # Adjust sleep time calculation to account for increased order volume
        self.next_sleep_time = self.calculate_sleep_time(remaining_time, self.number_trades, self.goal * self.order_multiplier)
        #print('next sleep time', self.next_sleep_time)
        print(
            "[INFORMED TRUE END CHECK]",
            "len_fills=", len(self.filled_orders),
            "sum_amount=", sum(fill["amount"] for fill in self.filled_orders),
            "target=", self.goal * self.order_multiplier,
            "remaining_time=", remaining_time,
            "open_orders=", len(self.orders),
            "open_order_prices=", [order["price"] for order in self.orders],
            "top_bid=", self.get_best_price(OrderType.BID),
            "top_ask=", self.get_best_price(OrderType.ASK),
            "use_passive_orders=", self.use_passive_orders,
            "num_passive_to_keep", self.num_passive_to_keep,
            "cond_aggressive=", cond_aggressive,
            "spread=", spread,
            "spread_ticks=", spread_ticks,
            "informed_edge=", self.informed_edge,
            "next_sleep_time=", self.next_sleep_time,
        )
                

    
    async def run(self) -> None:
        while not self._stop_requested.is_set():
            try:
                await self.maybe_sleep()
                await self.check()
                await asyncio.sleep(self.next_sleep_time)
            except asyncio.CancelledError:
                #print("Run method cancelled, performing cleanup...")
                break
            except Exception as e:
                print(f"An error occurred in InformedTrader run loop: {e}")
                traceback.print_exc()
                break

        await self.cancel_all_outstanding_orders()

    async def handle_TRADING_STARTED(self, data):
        """
        Reset the start_time when trading actually begins.
        """
        await super().handle_TRADING_STARTED(data)