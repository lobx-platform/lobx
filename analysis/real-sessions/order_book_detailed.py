"""
Uses results from order_book to construct a detailed view 
"""

import os
import pandas as pd
import numpy as np

from settings import DATE, DAYSTATS_DIR

input_file = os.path.join(DAYSTATS_DIR, f"OB_{DATE}.csv")

output_ob_detailed = os.path.join(DAYSTATS_DIR, f"OBDetailed_{DATE}.csv")
output_markets = os.path.join(DAYSTATS_DIR, f"markets_{DATE}.csv")

df = pd.read_csv(input_file)


df['Datetime'] = pd.to_datetime(df.Timestamp)

df_sorted = df.sort_values(by=['Trader', 'Market', 'Datetime'])

df_sorted['Time'] = df_sorted.groupby('Market')['Datetime'].transform(lambda x: (x - x.iloc[0]).dt.total_seconds())



market_available = list(df_sorted.Market.unique())

n_markets = len(market_available)

all_markets_OB = pd.DataFrame()
all_markets_metrics = pd.DataFrame()

j = 0
for market in market_available:
    j += 1
    print('market is', market,  f'{j} out of {n_markets}')
    df_market_i = df_sorted.loc[df_sorted.Market == market].reset_index(drop=True)
    treatment = df_market_i.Treatment.iloc[0]
    informed_passive = df_market_i.Informed_Passive.iloc[0]
    IPR = df_market_i.IPR.iloc[0]
    informed_direction = df_market_i.Informed_Direction.iloc[0]
    
    #df_market_i['Trader_IM'] = df_market_i['Trader_IM'].apply(lambda x: "'HUMAN_'" if x.startswith("'HUMAN_") else x)
    
    df_market_i['Trader_IM'] = df_market_i['Trader_IM'].apply(lambda x: "'HUMAN_'" if isinstance(x, str) and x.startswith("'HUMAN_") else x)
    
    new_df_i = pd.DataFrame()
    
    bids = []
    asks = []
    num_trades = 0
    
    
    for i in range(df_market_i.shape[0]):
        row_df = df_market_i.iloc[i]
        #print(row_df)
        #print('------')
        trader = row_df['Trader']
        market = row_df['Market']
        
        trader_im = row_df['Trader_IM']
        price = row_df['Trader_IM_Price']
        amount = row_df['Trader_IM_Amount']
        direction = row_df['Trader_IM_Direction']
        order_type = row_df['Trader_IM_Type']
        datetime = row_df['Datetime']
        time = row_df['Time']
        
        liquidity_provider = None
        liquidity_taker = None
        aggressive_order = 'No'
        
        if i ==0:
            if order_type == 'ADD_ORDER':
                if direction == 'BID':
                    new_order = {'Trader': trader_im, 'Timestamp': datetime, 'Price': price, 'Amount': amount, 'Direction': direction}
                    bids.append(new_order)
                else:
                    new_order = {'Trader': trader_im, 'Timestamp': datetime, 'Price': price, 'Amount': amount, 'Direction': direction}
                    asks.append(new_order)
        
        
        if bids:
            best_bid_price = max(order['Price'] for order in bids)
        else:
            best_bid_price = None
            
        if asks:
            best_ask_price = min(order['Price'] for order in asks)
        else:
            best_ask_price = None       
        
        if i >0:
            if order_type == 'ADD_ORDER':
                if direction == 'BID':
                    if best_ask_price is not None:
                        if price >= best_ask_price:
                            best_ask = min(asks, key=lambda ask: (ask["Price"], ask["Timestamp"]))
                            best_ask_trader = best_ask['Trader']
                            liquidity_provider = best_ask_trader
                            liquidity_taker = trader_im
                            num_trades += 1
                            aggressive_order = 'Yes'
                            
                            order_to_remove = best_ask
                            asks.remove(best_ask)
                        else:
                            new_order = {'Trader': trader_im, 'Timestamp': datetime, 'Price': price, 'Amount': amount, 'Direction': direction}
                            bids.append(new_order)
                    else:
                        new_order = {'Trader': trader_im, 'Timestamp': datetime, 'Price': price, 'Amount': amount, 'Direction': direction}
                        bids.append(new_order)
                        
                    
                elif direction == 'ASK':
                    if best_bid_price is not None: 
                        if price <= best_bid_price:
                            best_bid = min(bids, key=lambda bid: (-bid["Price"], bid["Timestamp"]))
                            best_bid_trader = best_bid['Trader']
                            liquidity_provider = best_bid_trader
                            liquidity_taker = trader_im
                            num_trades += 1
                            aggressive_order = 'Yes'
                            
                            order_to_remove = best_bid
                            bids.remove(best_bid)
                        else:
                            new_order = {'Trader': trader_im, 'Timestamp': datetime, 'Price': price, 'Amount': amount, 'Direction': direction}
                            asks.append(new_order)
                    else:
                        new_order = {'Trader': trader_im, 'Timestamp': datetime, 'Price': price, 'Amount': amount, 'Direction': direction}
                        asks.append(new_order)
                
            elif order_type == 'CANCEL_ORDER':
                if direction == 'BID':
                    filtered_bids = [bid for bid in bids if bid["Trader"] == trader_im and bid["Price"] == price]
                    
                    if filtered_bids:
                        latest_bid = max(filtered_bids, key=lambda bid: bid["Timestamp"])
                        bids.remove(latest_bid)
                    
                    
                if direction == 'ASK':
                    filtered_asks = [ask for ask in asks if ask["Trader"] == trader_im and ask["Price"] == price]
                    
                    if filtered_asks:
                        latest_ask = max(filtered_asks, key=lambda ask: ask["Timestamp"])
                        asks.remove(latest_ask)
                        
    
        
        
        best_bid_price = max(order['Price'] for order in bids) if bids else None
        best_ask_price = min(order['Price'] for order in asks) if asks else None
        
        if best_bid_price is not None:
            best_bid_size = sum(order['Amount'] for order in bids if order['Price'] == best_bid_price)
        else:
            best_bid_size = 0
        
        
        if best_ask_price is not None:
            best_ask_size = sum(order['Amount'] for order in asks if order['Price'] == best_ask_price)
        else:
            best_ask_size = 0
        
        
        if best_bid_price is not None and best_ask_price is not None:
            midprice = (best_bid_price + best_ask_price) / 2
        else:
            midprice = None
        
        
        sorted_bid_prices = sorted({order['Price'] for order in bids}, reverse=True)
        
        best_bid_price_2 = sorted_bid_prices[1] if len(sorted_bid_prices) > 1 else None
        
        if best_bid_price_2 is not None:
            best_bid_size_2 = sum(order['Amount'] for order in bids if order['Price'] == best_bid_price_2)
        else:
            best_bid_size_2 = 0
        
        best_bid_price_3 = sorted_bid_prices[2] if len(sorted_bid_prices) > 2 else None
        
        if best_bid_price_3 is not None:
            best_bid_size_3 = sum(order['Amount'] for order in bids if order['Price'] == best_bid_price_3)
        else:
            best_bid_size_3 = 0
            
        best_bid_price_4 = sorted_bid_prices[3] if len(sorted_bid_prices) > 3 else None
        
        if best_bid_price_4 is not None:
            best_bid_size_4 = sum(order['Amount'] for order in bids if order['Price'] == best_bid_price_4)
        else:
            best_bid_size_4 = 0    

        best_bid_price_5 = sorted_bid_prices[4] if len(sorted_bid_prices) > 4 else None
        
        if best_bid_price_5 is not None:
            best_bid_size_5 = sum(order['Amount'] for order in bids if order['Price'] == best_bid_price_5)
        else:
            best_bid_size_5 = 0 


        sorted_ask_prices = sorted({order['Price'] for order in asks})
        
        best_ask_price_2 = sorted_ask_prices[1] if len(sorted_ask_prices) > 1 else None

        if best_ask_price_2 is not None:
            best_ask_size_2 = sum(order['Amount'] for order in asks if order['Price'] == best_ask_price_2)
        else:
            best_ask_size_2 = 0
        
        best_ask_price_3 = sorted_ask_prices[2] if len(sorted_ask_prices) > 2 else None

        if best_ask_price_3 is not None:
            best_ask_size_3 = sum(order['Amount'] for order in asks if order['Price'] == best_ask_price_3)
        else:
            best_ask_size_3 = 0
        
        best_ask_price_4 = sorted_ask_prices[3] if len(sorted_ask_prices) > 3 else None

        if best_ask_price_4 is not None:
            best_ask_size_4 = sum(order['Amount'] for order in asks if order['Price'] == best_ask_price_4)
        else:
            best_ask_size_4 = 0
            
        best_ask_price_5 = sorted_ask_prices[4] if len(sorted_ask_prices) > 4 else None

        if best_ask_price_5 is not None:
            best_ask_size_5 = sum(order['Amount'] for order in asks if order['Price'] == best_ask_price_5)
        else:
            best_ask_size_5 = 0



        # report and save line
        new_line = {'Trader': [trader],
                    'Market': [market],
                    'Treatment': [treatment],
                    'Informed_Passive': [informed_passive],
                    'IPR': [IPR],
                    'Informed_Direction': [informed_direction],
                    'Timestamp':[datetime],
                    'Time': [time],
                    'Bid_Price_1': [best_bid_price],
                    'Bid_Size_1': [best_bid_size],
                    'Bid_Price_2': [best_bid_price_2],
                    'Bid_Size_2': [best_bid_size_2],
                    'Bid_Price_3': [best_bid_price_3],
                    'Bid_Size_3': [best_bid_size_3],
                    'Bid_Price_4': [best_bid_price_4],
                    'Bid_Size_4': [best_bid_size_4],
                    'Bid_Price_5': [best_bid_price_5],
                    'Bid_Size_5': [best_bid_size_5],
                    
                    'Ask_Price_1': [best_ask_price],
                    'Ask_Size_1': [best_ask_size],
                    'Ask_Price_2': [best_ask_price_2],
                    'Ask_Size_2': [best_ask_size_2],
                    'Ask_Price_3': [best_ask_price_3],
                    'Ask_Size_3': [best_ask_size_3],
                    'Ask_Price_4': [best_ask_price_4],
                    'Ask_Size_4': [best_ask_size_4],
                    'Ask_Price_5': [best_ask_price_5],
                    'Ask_Size_5': [best_ask_size_5],
                    
                    'Midprice': [midprice],
                    'Trader_IM': [trader_im],
                    'Trader_IM_Price': [price],
                    'Trader_IM_Amount': [amount],
                    'Trader_IM_Direction': [direction],
                    'Trader_IM_Type': [order_type],
                    'Aggressive_Order': [aggressive_order],
                    'Liquidity_Taker': [liquidity_taker],
                    'Liquidity_Provider': [liquidity_provider],
                    }
        
        new_line_df = pd.DataFrame(new_line)
        
        new_df_i = pd.concat([new_df_i,new_line_df],axis=0)
    
    new_df_i = new_df_i.reset_index(drop=True)
    
  
    initial_midprice = new_df_i['Midprice'].loc[new_df_i['Midprice'].first_valid_index()]
    final_midprice = new_df_i['Midprice'].loc[new_df_i['Midprice'].last_valid_index()]
    final_best_bid_price = new_df_i['Bid_Price_1'].loc[new_df_i['Bid_Price_1'].last_valid_index()]
    final_best_ask_price = new_df_i['Ask_Price_1'].loc[new_df_i['Ask_Price_1'].last_valid_index()]

 
    total_human_trades = (new_df_i['Liquidity_Taker'] == "'HUMAN_'").sum() + (new_df_i['Liquidity_Provider'] == "'HUMAN_'").sum() 


    mask_1_human_buy_trades = (new_df_i['Liquidity_Taker'] == "'HUMAN_'") & (new_df_i['Trader_IM_Direction'] == 'BID')
    mask_2_human_buy_trades = (new_df_i['Liquidity_Provider'] == "'HUMAN_'") & (new_df_i['Trader_IM_Direction'] == 'ASK')
    
    mask_1_human_sell_trades = (new_df_i['Liquidity_Taker'] == "'HUMAN_'") & (new_df_i['Trader_IM_Direction'] == 'ASK')
    mask_2_human_sell_trades = (new_df_i['Liquidity_Provider'] == "'HUMAN_'") & (new_df_i['Trader_IM_Direction'] == 'BID')

    
    human_buy_trades = new_df_i.loc[mask_1_human_buy_trades | mask_2_human_buy_trades].shape[0]
    human_buy_prices = new_df_i.loc[mask_1_human_buy_trades | mask_2_human_buy_trades].Trader_IM_Price.tolist()
    human_buy_vwap = np.mean(human_buy_prices)
    
    human_sell_trades = new_df_i.loc[mask_1_human_sell_trades | mask_2_human_sell_trades].shape[0]
    human_sell_prices = new_df_i.loc[mask_1_human_sell_trades | mask_2_human_sell_trades].Trader_IM_Price.tolist()
    human_sell_vwap = np.mean(human_sell_prices)
    

    
    if human_buy_trades == human_sell_trades:
        pnl_original = np.sum(human_sell_prices) - np.sum(human_buy_prices)
        #pnl_new = pnl_original
    elif human_buy_trades > human_sell_trades:
        new_human_sell_prices = human_sell_prices + [final_best_bid_price -2] * (human_buy_trades - human_sell_trades)
        pnl_original = np.sum(new_human_sell_prices) - np.sum(human_buy_prices)
        
        #new_human_sell_prices_2 = human_sell_prices + [x+1 for x in human_buy_prices[len(human_sell_prices):]]
        #pnl_new = np.sum(new_human_sell_prices_2) - np.sum(human_buy_prices)
        
    else:
        new_human_buy_prices = human_buy_prices + [final_best_ask_price + 2] * (human_sell_trades - human_buy_trades)
        pnl_original = np.sum(human_sell_prices) - np.sum(new_human_buy_prices)
        
        #new_human_buy_prices_2 = human_buy_prices + [x-1 for x in human_sell_prices[len(human_buy_prices):]]
        #pnl_new = np.sum(human_sell_prices) - np.sum(new_human_buy_prices_2)


    pnl_original_per_transaction = (
        pnl_original / max(human_buy_trades, human_sell_trades)
        if max(human_buy_trades, human_sell_trades) != 0
        else 0
        )
    
    #pnl_new_per_transaction = (
    #   pnl_new / max(human_buy_trades, human_sell_trades)
    #    if max(human_buy_trades, human_sell_trades) != 0
    #    else 0
    #    )
    
    
    #mask_informed_trades = (new_df_i['Liquidity_Taker'] == "'INFORMED_1'") | (new_df_i['Liquidity_Provider'] == "'INFORMED_1'")
    
    mask_informed_trades = (new_df_i['Liquidity_Taker'].astype(str).str.contains("INFORMED", na=False) | new_df_i['Liquidity_Provider'].astype(str).str.contains("INFORMED", na=False))
    
    
    #informed_trade_prices = new_df_i.loc[mask_informed_trades].Trader_IM_Price.tolist()
    #informed_trades = len(informed_trade_prices)
    #informed_vwap = np.mean(informed_trade_prices)
    #informed_slippage = initial_midprice - informed_vwap
    #informed_slippage_scaled = informed_slippage / np.sqrt(informed_trades)

    informed_trade_prices = new_df_i.loc[mask_informed_trades, 'Trader_IM_Price'].tolist()
    informed_trades = len(informed_trade_prices)

    if informed_trades > 0:
        informed_vwap = np.mean(informed_trade_prices)
        informed_slippage = initial_midprice - informed_vwap
        informed_slippage_scaled = informed_slippage / np.sqrt(informed_trades)
    else:
        informed_vwap = np.nan
        informed_slippage = np.nan
        informed_slippage_scaled = np.nan



    
    if human_buy_trades > human_sell_trades:
        platform_buy_shares = human_buy_trades - human_sell_trades
        last_row = new_df_i.iloc[-1]
        for jj in range(platform_buy_shares):
            new_row = { 'Trader':last_row['Trader'],
                       'Market':last_row['Market'],
                       'Treatment': last_row['Treatment'],
                       'Informed_Passive': last_row['Informed_Passive'],
                       'IPR': last_row['IPR'],
                       'Informed_Direction': last_row['Informed_Direction'],
                       'Timestamp': last_row['Timestamp'] ,
                       'Time': last_row['Time'] ,
                       'Bid_Price_1': last_row['Bid_Price_1'],
                       'Bid_Size_1': last_row['Bid_Size_1'],
                       'Ask_Price_1': last_row['Ask_Price_1'],
                       'Ask_Size_1': last_row['Ask_Size_1'],
                       'Midprice': last_row['Midprice'],
                       'Trader_IM': "'PLATFORM'",
                       'Trader_IM_Price': initial_midprice,
                       'Trader_IM_Amount': [1],
                       'Trader_IM_Direction': 'BID',
                       'Trader_IM_Type': ['OFFLINE_ORDER_1'],
                       'Aggressive_Order': ['Yes'],
                       'Liquidity_Taker': ["'PLATFORM'"],
                       'Liquidity_Provider': ["'HUMAN_'"],
                }
    
            new_row_df = pd.DataFrame(new_row)
            new_df_i = pd.concat([new_df_i,new_row_df],axis=0)
        
        human_buy_prices_left = human_buy_prices[len(human_sell_prices):]  
        for new_price in human_buy_prices_left:
            new_row = { 'Trader':last_row['Trader'],
                       'Market':last_row['Market'],
                       'Treatment': last_row['Treatment'],
                       'Informed_Passive': last_row['Informed_Passive'],
                       'IPR': last_row['IPR'],
                       'Informed_Direction': last_row['Informed_Direction'],
                       'Timestamp': last_row['Timestamp'] ,
                       'Time': last_row['Time'] ,
                       'Bid_Price_1': last_row['Bid_Price_1'],
                       'Bid_Size_1': last_row['Bid_Size_1'],
                       'Ask_Price_1': last_row['Ask_Price_1'],
                       'Ask_Size_1': last_row['Ask_Size_1'],
                       'Midprice': last_row['Midprice'],
                       'Trader_IM': "'PLATFORM'",
                       'Trader_IM_Price': new_price - 1,
                       'Trader_IM_Amount': [1],
                       'Trader_IM_Direction': 'ASK',
                       'Trader_IM_Type': ['OFFLINE_ORDER_2'],
                       'Aggressive_Order': ['Yes'],
                       'Liquidity_Taker': ["'PLATFORM'"],
                       'Liquidity_Provider': ["'HUMAN_'"],
                }
    
            new_row_df = pd.DataFrame(new_row)
            new_df_i = pd.concat([new_df_i,new_row_df],axis=0)
        
            
            
            
    elif human_sell_trades > human_buy_trades:
        platform_sell_shares = human_sell_trades - human_buy_trades
        last_row = new_df_i.iloc[-1]
        for jj in range(platform_sell_shares):
            new_row = { 'Trader':last_row['Trader'],
                       'Market':last_row['Market'],
                       'Treatment': last_row['Treatment'],
                       'Informed_Passive': last_row['Informed_Passive'],
                       'IPR': last_row['IPR'],
                       'Informed_Direction': last_row['Informed_Direction'],
                       'Timestamp': last_row['Timestamp'] ,
                       'Time': last_row['Time'] ,
                       'Bid_Price_1': last_row['Bid_Price_1'],
                       'Bid_Size_1': last_row['Bid_Size_1'],
                       'Ask_Price_1': last_row['Ask_Price_1'],
                       'Ask_Size_1': last_row['Ask_Size_1'],
                       'Midprice': last_row['Midprice'],
                       'Trader_IM': "'PLATFORM'",
                       'Trader_IM_Price': initial_midprice,
                       'Trader_IM_Amount': [1],
                       'Trader_IM_Direction': 'ASK',
                       'Trader_IM_Type': ['OFFLINE_ORDER_1'],
                       'Aggressive_Order': ['Yes'],
                       'Liquidity_Taker': ["'PLATFORM'"],
                       'Liquidity_Provider': ["'HUMAN_'"],
                }
    
            new_row_df = pd.DataFrame(new_row)
            new_df_i = pd.concat([new_df_i,new_row_df],axis=0)

        human_sell_prices_left = human_sell_prices[len(human_buy_prices):]  
        for new_price in human_sell_prices_left:
            new_row = { 'Trader':last_row['Trader'],
                       'Market':last_row['Market'],
                       'Treatment': last_row['Treatment'],
                       'Informed_Passive': last_row['Informed_Passive'],
                       'IPR': last_row['IPR'],
                       'Informed_Direction': last_row['Informed_Direction'],
                       'Timestamp': last_row['Timestamp'] ,
                       'Time': last_row['Time'] ,
                       'Bid_Price_1': last_row['Bid_Price_1'],
                       'Bid_Size_1': last_row['Bid_Size_1'],
                       'Ask_Price_1': last_row['Ask_Price_1'],
                       'Ask_Size_1': last_row['Ask_Size_1'],
                       'Midprice': last_row['Midprice'],
                       'Trader_IM': "'PLATFORM'",
                       'Trader_IM_Price': new_price + 1,
                       'Trader_IM_Amount': [1],
                       'Trader_IM_Direction': 'ASK',
                       'Trader_IM_Type': ['OFFLINE_ORDER_2'],
                       'Aggressive_Order': ['Yes'],
                       'Liquidity_Taker': ["'PLATFORM'"],
                       'Liquidity_Provider': ["'HUMAN_'"],
                }
    
            new_row_df = pd.DataFrame(new_row)
            new_df_i = pd.concat([new_df_i,new_row_df],axis=0)
            
        
    all_markets_OB = pd.concat([all_markets_OB,new_df_i],axis=0)
    
    
    
    
    market_i_metrics = {
        'Trader': [trader],
        'Market': [market],
        'Treatment': [treatment],
        'Informed_Passive': [informed_passive],
        'IPR': [IPR],
        'Informed_Direction': [informed_direction],
        'Initial_Midprice': [initial_midprice],
        'Final_Midprice': [final_midprice],
        'PnL_Original': [pnl_original],
        'PnL_Original_per_transaction': [pnl_original_per_transaction],
        #'PnL_New': [pnl_new],
        #'PnL_New_per_transaction': [pnl_new_per_transaction],
        'Human_Num_Buy_Trades': [human_buy_trades],
        'Human_Num_Sell_Trades': [human_sell_trades],
        'Human_Buy_VWAP': [human_buy_vwap],
        'Human_Sell_VWAP': [human_sell_vwap],
        'Informed_Machine_VWAP': [informed_vwap],
        'Informed_Machine_Slippage': [informed_slippage],
        'Informed_Machine_Slippage_Scaled': [informed_slippage_scaled],
        'Informed_Machine_Trades': [informed_trades]
        }
    
    market_i_metrics_df = pd.DataFrame(market_i_metrics)
    
    all_markets_metrics = pd.concat([all_markets_metrics,market_i_metrics_df],axis=0)


all_markets_OB = all_markets_OB.reset_index(drop=True)

all_markets_metrics = all_markets_metrics.reset_index(drop=True)

all_markets_OB.to_csv(output_ob_detailed, index=False)
all_markets_metrics.to_csv(output_markets, index=False)
