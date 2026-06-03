import pandas as pd
import numpy as np
import random

def logfile_to_message(logfile_name):
    log_file_path = logfile_name
    timestamp_save = []
    price_save = []
    amount_save = []
    direction_save = []
    trader_save = []
    type_save = []
    trader_recorded = []


    with open(log_file_path, 'r') as log_file:
        for line in log_file:
            timestamp_str, level, msg = line.split(" - ", 2)
            msg_type, msg_content = msg.split(": ", 1)

            if msg_type == 'ADD_ORDER':

                amount_key = "'amount': "
                start_index = msg_content.index(amount_key) + len(amount_key)
                end_index = msg_content.index(',', start_index)
                amount_str = msg_content[start_index:end_index].strip()  # Extract and strip whitespace
                amount = float(amount_str)

                price_key = "'price': "
                start_index = msg_content.index(price_key) + len(price_key)
                end_index = msg_content.index(',', start_index)
                price_str = msg_content[start_index:end_index].strip()  # Extract and strip whitespace
                price = float(price_str)

                direction_key = "<OrderType."
                start_index = msg_content.index(direction_key) + len(direction_key)
                end_index = msg_content.index(':', start_index)
                direction_str = msg_content[start_index:end_index].strip()  # Extract and strip whitespace
                direction = direction_str

                trader_key = "'trader_id': "
                start_index = msg_content.index(trader_key) + len(trader_key)
                end_index = msg_content.index(',', start_index)
                trader_str = msg_content[start_index:end_index].strip()  # Extract and strip whitespace
                trader_type = (trader_str)

                price_save.append(price)
                amount_save.append(amount)
                direction_save.append(direction)
                trader_save.append(trader_type)
                timestamp_save.append(timestamp_str)
                type_save.append(msg_type)

            if msg_type == 'CANCEL_ORDER':

                amount_key = "'amount': "
                start_index = msg_content.index(amount_key) + len(amount_key)
                end_index = msg_content.index(',', start_index)
                amount_str = msg_content[start_index:end_index].strip()  # Extract and strip whitespace
                amount = float(amount_str)

                price_key = "'price': "
                start_index = msg_content.index(price_key) + len(price_key)
                end_index = msg_content.index(',', start_index)
                price_str = msg_content[start_index:end_index].strip()  # Extract and strip whitespace
                price = float(price_str)


                direction_key = "<OrderType."
                start_index = msg_content.index(direction_key) + len(direction_key)
                end_index = msg_content.index(':', start_index)
                direction_str = msg_content[start_index:end_index].strip()  # Extract and strip whitespace
                direction = direction_str

                trader_key = "'trader_id': "
                start_index = msg_content.index(trader_key) + len(trader_key)
                end_index = msg_content.index(',', start_index)
                trader_str = msg_content[start_index:end_index].strip()  # Extract and strip whitespace
                trader_type = (trader_str)

                price_save.append(price)
                amount_save.append(amount)
                direction_save.append(direction)
                trader_save.append(trader_type)
                timestamp_save.append(timestamp_str)
                type_save.append(msg_type)

            if msg_type == 'RECORD_KEEPING_ORDER':
                trader_key = "'trader_id': "
                start_index = msg_content.index(trader_key) + len(trader_key)
                end_index = msg_content.index(',', start_index)
                trader_str = msg_content[start_index:end_index].strip()  # Extract and strip whitespace
                trader_type_recorded = (trader_str)
                trader_recorded.append(trader_type_recorded)




    df = pd.DataFrame({'Timestamp': timestamp_save,
                  'Price': price_save,
                  'Amount': amount_save,
                  'Direction': direction_save,
                  'Type' : type_save,
                  'Trader': trader_save})

    df['Timestamp'] = pd.to_datetime(df['Timestamp'].str.replace(',', '.'), format='%Y-%m-%d %H:%M:%S.%f')


    return df, trader_recorded




def get_best_ask_order(orders):
    best_ask_order = min(orders['ASKS'], key=lambda x: (x['Price'], x['Timestamp']))
    return best_ask_order


def get_best_bid_order(orders):
    best_bid_price = max(order['Price'] for order in orders['BIDS'])

    orders_to_check = []
    for order in orders['BIDS']:
        if order['Price'] == best_bid_price:
            orders_to_check.append(order)

    best_bid_order = min(orders_to_check, key=lambda x:  x['Timestamp'])
    return best_bid_order


def get_random_order(orders,trader):
    random_orders = []
    for order in orders:
        if order['Trader'] == trader:
            random_orders.append(order)

    if random_orders:
        return_order = random.choice(random_orders)
    else:
        return_order = {}

    return return_order

def get_order_to_cancel(orders,trader,price):
    orders_trader = [order for order in orders if order['Trader'] ==trader]
    orders_at_price = [order for order in orders_trader if order['Price'] ==price]

    if orders_at_price:
        order_to_cancel = max(orders_at_price, key=lambda order: order['Timestamp'])
        return order_to_cancel
    else:
        return None



def order_book_contruction(logfile_name):
    message_df, all_metrics = process_logfile(logfile_name)
    return all_metrics

def process_logfile(logfile_name):
    message_df, trader_type_recorded  = logfile_to_message(logfile_name)
    all_traders = list(np.unique(message_df.Trader))

    if trader_type_recorded and trader_type_recorded not in all_traders:
        all_traders = all_traders + [trader_type_recorded]

    trades_by_human = {}
    trades_by_informed_machine = {}


    for trader in all_traders:
        if 'HUMAN' in trader:
            trades_by_human[trader] = []
        if 'INFORMED' in trader:
            trades_by_informed_machine[trader] = []

    orders = {'BIDS': [],'ASKS': []}
    total_trades = 0
    total_cancellations = 0
    all_midprices = []
    all_best_bid_prices = []
    all_best_ask_prices = []

    start_time = message_df['Timestamp'].iloc[0]
    message_df['New_Timestamp'] = (message_df['Timestamp'] - start_time).dt.total_seconds()
    order_book = pd.DataFrame()

    for index, row in message_df.iterrows():
        timestamp = row['Timestamp']
        price = row['Price']
        amount = row['Amount']
        direction = row['Direction']
        order_type = row['Type']
        trader = row['Trader']

        new_order = {'Timestamp':timestamp,
                     'Price': price,
                     'Amount':amount,
                     'Direction': direction,
                     'Trader':trader}

        best_bid_price = max((order['Price'] for order in orders['BIDS']), default=None)
        best_ask_price = min((order['Price'] for order in orders['ASKS']), default=None)


        if 'INFORMED' in trader:
            if direction == 'BID':
                informed_direction = 'Buy'
            else:
                informed_direction = 'Sell'

        if order_type =='ADD_ORDER':
            if direction == 'BID':
                if best_ask_price is None:
                    orders['BIDS'].append(new_order)
                elif price < best_ask_price:
                    orders['BIDS'].append(new_order)
                else:
                    order_to_remove = get_best_ask_order(orders)
                    orders['ASKS'].remove(order_to_remove)
                    total_trades +=1
                    if trader in trades_by_human:
                        trades_by_human[trader].append({'Price': order_to_remove['Price'],
                                                        'Amount': order_to_remove['Amount'],
                                                        'Type': 'Buy'})
                    if order_to_remove['Trader'] in trades_by_human:
                        name_to_use = order_to_remove['Trader']
                        trades_by_human[name_to_use].append({'Price': order_to_remove['Price'],
                                                        'Amount': order_to_remove['Amount'],
                                                        'Type': 'Sell'})
                    if trader in trades_by_informed_machine:
                        trades_by_informed_machine[trader].append({'Price': order_to_remove['Price'],
                                                        'Amount': order_to_remove['Amount'],
                                                        'Type': 'Buy'})
                    if order_to_remove['Trader'] in trades_by_informed_machine:
                        name_to_use = order_to_remove['Trader']
                        trades_by_informed_machine[name_to_use].append({'Price': order_to_remove['Price'],
                                                        'Amount': order_to_remove['Amount'],
                                                        'Type': 'Sell'})

            else:
                if best_bid_price is None:
                    orders['ASKS'].append(new_order)
                elif price > best_bid_price:
                    orders['ASKS'].append(new_order)
                else:
                    order_to_remove = get_best_bid_order(orders)
                    orders['BIDS'].remove(order_to_remove)
                    total_trades +=1
                    if trader in trades_by_human:
                        trades_by_human[trader].append({'Price': order_to_remove['Price'],
                                                        'Amount': order_to_remove['Amount'],
                                                        'Type': 'Sell'})
                    if order_to_remove['Trader'] in trades_by_human:
                        name_to_use = order_to_remove['Trader']
                        trades_by_human[name_to_use].append({'Price': order_to_remove['Price'],
                                                        'Amount': order_to_remove['Amount'],
                                                        'Type': 'Buy'})
                    if trader in trades_by_informed_machine:
                        trades_by_informed_machine[trader].append({'Price': order_to_remove['Price'],
                                                        'Amount': order_to_remove['Amount'],
                                                        'Type': 'Sell'})
                    if order_to_remove['Trader'] in trades_by_informed_machine:
                        name_to_use = order_to_remove['Trader']
                        trades_by_informed_machine[name_to_use].append({'Price': order_to_remove['Price'],
                                                        'Amount': order_to_remove['Amount'],
                                                        'Type': 'Buy'})

        elif order_type == 'CANCEL_ORDER':
            if direction == 'BID':
                if orders['BIDS']:
                    order_to_cancel = get_order_to_cancel(orders['BIDS'], trader, price)
                    if order_to_cancel:
                        orders['BIDS'].remove(order_to_cancel)
                        total_cancellations +=1
            else:
                if orders['ASKS']:
                    order_to_cancel = get_order_to_cancel(orders['ASKS'], trader, price)
                    if order_to_cancel:
                        orders['ASKS'].remove(order_to_cancel)
                        total_cancellations +=1


        best_bid_price = max((order['Price'] for order in orders['BIDS']), default=None)
        best_ask_price = min((order['Price'] for order in orders['ASKS']), default=None)

        best_ask_size = (
            sum(order['Amount'] for order in orders['ASKS'] if order['Price'] == best_ask_price)
            if best_ask_price is not None else None
        )

        best_bid_size = (
            sum(order['Amount'] for order in orders['BIDS'] if order['Price'] == best_bid_price)
            if best_bid_price is not None else None
        )

        order_book_i = pd.DataFrame({
            'Timestamp': [timestamp],
            'Bid_Price_1': [best_bid_price],
            'Ask_Price_1': [best_ask_price],
            'Bid_Size_1': [best_bid_size],
            'Ask_Size_1': [best_ask_size],
        })

        order_book = pd.concat([order_book,order_book_i],axis=0)


        if (best_bid_price is not None) and (best_ask_price is not None):
            midprice = (best_bid_price + best_ask_price) / 2
            all_best_bid_prices.append(best_bid_price)
            all_best_ask_prices.append(best_ask_price)
            all_midprices.append(midprice)


    all_metrics = {'Total_Orders': message_df.shape[0],
                   'Total_Trades': total_trades,
                   'Total_Cancellations': total_cancellations,
                   'Initial_Midprice': all_midprices[0],
                   'Last_Midprice': all_midprices[-1],
                   'Informed_Direction': informed_direction}

    # get informed machine statistics
    for trader in trades_by_informed_machine:
        trades = trades_by_informed_machine[trader]
        total_trades = sum(trade['Amount'] for trade in trades)
        total_expenditure = sum(trade['Price'] for trade in trades)
        informed_vwap = total_expenditure / total_trades
        direction = trades[0]['Type']
        if direction == 'Sell':
            splippage = informed_vwap - all_metrics['Initial_Midprice']
        if direction == 'Buy':
            splippage = all_metrics['Initial_Midprice'] - informed_vwap
        scaled_slippage = float(splippage / np.sqrt(total_trades))

        all_metrics[trader] = {
            'VWAP': round(informed_vwap,3),
            'Slippage': round(splippage,3),
            'Scaled_Slippage': round(scaled_slippage,3),
            'Trades': int(total_trades)
        }

    for trader in trades_by_human:
        trades_human_i = trades_by_human[trader]
        all_amounts = []
        all_prices = []

        num_buy = 0
        num_sell = 0
        prices_buy = []
        prices_sell = []
        for trade in trades_human_i:
            all_amounts.append(trade['Amount'])
            all_prices.append(trade['Price'])
            if trade['Type'] == 'Buy':
                prices_buy.append(trade['Price'])
                num_buy +=1
            else:
                prices_sell.append(trade['Price'])
                num_sell +=1

        total_trades_trader_i = sum(all_amounts)
        trader_i_vwap = sum(all_prices) / total_trades_trader_i if total_trades_trader_i > 0 else 0

        if num_buy == num_sell:
            pnl_original = sum(prices_sell) - sum(prices_buy)
            pnl_new = pnl_original
            penalty_original = 0
            penalty_new = 0
        elif num_buy > num_sell:
            prices_buy_rem = prices_buy[num_sell:]
            vwap_prices_buy_rem = sum(prices_buy_rem) / len(prices_buy_rem)
            penalty = sum([ price - 1 for price in prices_buy_rem])
            pnl_new = sum(prices_sell) - sum(prices_buy) + penalty
            penalty_new = (num_buy - num_sell) * (penalty/len(prices_buy_rem) -  np.mean(prices_buy_rem) )

            pnl_original = sum(prices_sell) - sum(prices_buy) + (num_buy - num_sell) * (all_best_bid_prices[-1] - 2)
            penalty_original = (num_buy - num_sell) * ((all_best_bid_prices[-1] - 2) - vwap_prices_buy_rem)
        else:
            prices_sell_rem = prices_sell[num_buy:]
            vwap_prices_sell_rem = sum(prices_sell_rem) / len(prices_sell_rem)
            penalty = sum([ price + 1 for price in prices_sell_rem])
            # since num_sell > num_buy
            # i need to buy the rest
            pnl_new = sum(prices_sell) - sum(prices_buy) - penalty
            penalty_new = (num_sell - num_buy) * (penalty/len(prices_sell_rem) -  np.mean(prices_sell_rem))

            pnl_original = sum(prices_sell) - sum(prices_buy) - (num_sell - num_buy) * (all_best_ask_prices[-1] + 2)
            penalty_original = (num_sell - num_buy) * (vwap_prices_sell_rem - (all_best_ask_prices[-1] + 2))

        all_metrics[trader] = {'Trades': total_trades_trader_i,
                               'VWAP': trader_i_vwap,
                               'PnL_Original': pnl_original,
                               'PnL_New': pnl_new,
                               'Penalty_Original': penalty_original,
                               'Penalty_New': penalty_new,
                               'Num_Sell': num_sell,
                               'Num_Buy': num_buy,
                               'Prices_Sell': prices_sell,
                               'Prices_Buy': prices_buy}

    return message_df, all_metrics, order_book



def calculate_trader_specific_metrics(trader_specific_metrics, general_metrics, trader_goal):
    """Calculate trader-specific metrics based on trading activity and goals."""
    # Store the original PnL
    pnl_original = trader_specific_metrics['PnL_Original']
    pnl_new = trader_specific_metrics['PnL_New']

    # Calculate reward with scaling between 3 and 10 based on PnL
    if isinstance(pnl_original, (int, float)):
        max_pnl_possible = 20
        max_gbp_to_give = 10
        if pnl_original<0:
            reward = 0
        else:
            ratio = pnl_original/max_pnl_possible
            real_ratio = min(ratio,1)
            reward = real_ratio * max_gbp_to_give
        # # Clip PnL to [-100, 100] range
        # capped_pnl = max(min(original_pnl, 100), -100)
        # # Scale PnL from [-100, 100] to [0, 1]
        # normalized_pnl = (capped_pnl + 100) / 200
        # # Scale to [3, 10] range
        # reward = 3 + (normalized_pnl * 7)
    else:
        reward = '-'

    if trader_goal != 0:
        if trader_goal > 0:
            if trader_specific_metrics['Trades'] <= trader_goal:
                remaining_trades = abs(abs(trader_goal) - abs(trader_specific_metrics['Trades']))
                expenditure = trader_specific_metrics['VWAP'] * trader_specific_metrics['Trades']
                total_expenditure = expenditure + remaining_trades * general_metrics['Last_Midprice'] * 1.5
                penalized_vwap = total_expenditure/abs(trader_goal)
                slippage = general_metrics['Initial_Midprice'] - penalized_vwap
                slippage_scaled = (general_metrics['Initial_Midprice'] - penalized_vwap) / np.sqrt(abs(trader_goal))

                trader_specific_metrics.update({
                    'Remaining_Trades': remaining_trades,
                    'Penalized_VWAP': penalized_vwap,
                    'Slippage': slippage,
                    'Slippage_Scaled': slippage_scaled,
                    'PnL_Original': pnl_original,  # Keep original PnL
                    'Reward': reward
                })
            else:
                remaining_trades = abs(trader_goal) - abs(trader_specific_metrics['Trades'])
                prices_buy = trader_specific_metrics['Prices_Buy']
                expenditure = sum(prices_buy[0:abs(trader_goal)])
                VWAP = expenditure / abs(trader_goal)
                trader_specific_metrics['VWAP'] = VWAP
                penalized_vwap = expenditure / abs(trader_goal)
                slippage = general_metrics['Initial_Midprice'] - penalized_vwap
                slippage_scaled = (general_metrics['Initial_Midprice'] - penalized_vwap) / np.sqrt(abs(trader_goal))

                trader_specific_metrics.update({
                    'Remaining_Trades': remaining_trades,
                    'Penalized_VWAP': penalized_vwap,
                    'Slippage': slippage,
                    'Slippage_Scaled': slippage_scaled,
                    'PnL_Original': pnl_original,
                    'Reward': reward
                })
        else:
            if trader_specific_metrics['Trades'] <= abs(trader_goal):
                remaining_trades = abs(abs(trader_goal) - abs(trader_specific_metrics['Trades']))
                expenditure = trader_specific_metrics['VWAP'] * trader_specific_metrics['Trades']
                total_expenditure = expenditure + remaining_trades * general_metrics['Last_Midprice'] * 0.5
                penalized_vwap = total_expenditure/abs(trader_goal)
                slippage = penalized_vwap - general_metrics['Initial_Midprice']
                slippage_scaled = (penalized_vwap - general_metrics['Initial_Midprice']) / np.sqrt(abs(trader_goal))

                trader_specific_metrics.update({
                    'Remaining_Trades': remaining_trades,
                    'Penalized_VWAP': penalized_vwap,
                    'Slippage': slippage,
                    'Slippage_Scaled': slippage_scaled,
                    'PnL_Original': pnl_original,
                    'PnL_New': pnl_new,
                    'Reward': reward
                })
            else:
                remaining_trades = abs(trader_specific_metrics['Trades']) - abs(trader_goal)
                prices_sell = trader_specific_metrics['Prices_Sell']
                expenditure = sum(prices_sell[0:abs(trader_goal)])
                VWAP = expenditure / abs(trader_goal)
                trader_specific_metrics['VWAP'] = VWAP
                penalized_vwap = expenditure / abs(trader_goal)
                slippage = penalized_vwap - general_metrics['Initial_Midprice']
                slippage_scaled = (penalized_vwap - general_metrics['Initial_Midprice']) / np.sqrt(abs(trader_goal))

                trader_specific_metrics.update({
                    'Remaining_Trades': remaining_trades,
                    'Penalized_VWAP': penalized_vwap,
                    'Slippage': slippage,
                    'Slippage_Scaled': slippage_scaled,
                    'PnL': pnl_original,
                    'Reward': reward
                })

    else:
        trader_specific_metrics.update({
            'Remaining_Trades': abs(trader_specific_metrics['Num_Sell'] - trader_specific_metrics['Num_Buy']),
            'VWAP': '-',
            'Penalized_VWAP': '-',
            'Slippage': '-',
            'Slippage_Scaled': '-',
            'PnL_Original': pnl_original,
            'Reward': reward
        })

    return trader_specific_metrics

if __name__ == '__main__':
    location = '/Users/marioljonuzaj/Dropbox/InformationDisseminatationProject/Pilot Sessions/Pilot Session October/T6/Logfiles/'
    logfile_name = location + 'SESSION_1761395103_ea141aff_trading.log'  # Replace with your log file path
    market_id = logfile_name.split('/')[-1].split('_trading')[0]
    print('logfile_name is:', logfile_name)
    print('market_id is:', market_id)
    logfile_to_message(logfile_name)
    message_df, all_metrics, order_book = process_logfile(logfile_name)


    print(all_metrics)
    print(order_book)

    #for value in all_metrics:
    #    if 'HUMAN_' in value:
    #        # Extract the rest of the string after 'Human_'
    #        human_id = value.split('HUMAN_', 1)[1]
    #    if 'INFORMED_' in value:
    #        informed_id = value

    #trader_specific_metrics = all_metrics["'HUMAN_" + human_id]


    #trader_specific_metrics = calculate_trader_specific_metrics(trader_specific_metrics, all_metrics, 0)
    #print(trader_specific_metrics)
    #output_message_file = location  + market_id + '_' + 'message_book.csv'
    #message_df.to_csv(output_message_file, index=False)

    #output_metrics_file = location  + market_id + '_' + ' metrics.json'

    # Save the dictionary to a JSON file
    # with open(output_metrics_file, 'w') as json_file:
    #     json.dump(all_metrics, json_file, indent=4)
