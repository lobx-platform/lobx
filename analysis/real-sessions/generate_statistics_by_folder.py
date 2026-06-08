import numpy as np
import pandas as pd
import os
from datetime import datetime

from functions import process_logfile, calculate_trader_specific_metrics

from settings import (BASE_DIR, FOLDERS, DATE, INFORMED_PASSIVE,
                      INFORMED_PAR_RATE, LOGFILES_SUBFOLDER,
                      DAYSTATS_SUBFOLDER, ORDER_BOOKS_SUBFOLDER)

folders = FOLDERS
informed_passive = INFORMED_PASSIVE
informed_par_rate = INFORMED_PAR_RATE
date_of_session = DATE

day_statistics = pd.DataFrame(columns=['Trader', 'Market', 'Informed_Direction', 'Informed_Passive', 'Informed_Participation_Rate',
                                       'PnL_Original', 'PnL_New','PnL_Original_per_transaction','PnL_New_per_transaction',
                                       'Penalty_Original','Penalty_New','Initial_Midprice', 'Last_Midprice',
                                       'Informed_Machine_VWAP','Informed_Machine_Slippage',
                                       'Informed_Machine_Scaled_Slippage', 'Informed_Machine_Trades',
                                       'Human_VWAP_Buy','Human_VWAP_Sell','Human_Rem_Trades'])

for index, folder in enumerate(folders):
    print(folder)
    logfiles_folder = os.path.join(BASE_DIR, folder, LOGFILES_SUBFOLDER)

    orderbook_folder = os.path.join(BASE_DIR, folder, ORDER_BOOKS_SUBFOLDER)

    os.makedirs(orderbook_folder, exist_ok=True)


    log_files = [logfiles_folder + '/' + f for f in os.listdir(logfiles_folder) if f.endswith('.log')]
    market_ids = [os.path.basename(p).replace('SESSION_', '').replace('MARKET_', '').replace('.log', '').replace('_', '_', 2) for p in log_files]

    jj = 0
    for logfile in log_files:
        print(logfile)
        jj += 1
        market_id = market_ids[jj-1]
        message_df, all_metrics, order_book = process_logfile(logfile)

        human_id = None
        informed_id = None
        informed_direction = [all_metrics['Informed_Direction']]

        for value in all_metrics:
            if 'HUMAN_' in value:
                # Extract the rest of the string after 'Human_'
                human_id = value.split('HUMAN_', 1)[1]
            if 'INFORMED_' in value:
                informed_id = value


        order_book['Midprice'] = (order_book['Bid_Price_1'] + order_book['Ask_Price_1']) / 2
        order_book['Trader_IM'] = message_df['Trader'].values
        order_book['Trader_IM_Price'] = message_df['Price'].values
        order_book['Trader_IM_Amount'] = message_df['Amount'].values
        order_book['Trader_IM_Direction'] = message_df['Direction'].values
        order_book['Trader_IM_Type'] = message_df['Type'].values

        order_book['Trader'] =  human_id[:-1] if human_id else None
        order_book['Market'] = market_id
        order_book['Treatment'] = folders[0]
        order_book['Informed_Passive'] = informed_passive[0]
        order_book['IPR'] = informed_par_rate[0]
        order_book['Informed_Direction'] = informed_direction[0]

        save_file_path_order_book = orderbook_folder + f'/{market_id}.csv'
        order_book.to_csv(save_file_path_order_book, index=False)



        if human_id is not None:
            trader_specific_metrics = all_metrics["'HUMAN_" + human_id]
            trader_specific_metrics = calculate_trader_specific_metrics(trader_specific_metrics, all_metrics, 0)

            keep_human_pnl_original = trader_specific_metrics['PnL_Original']
            keep_human_pnl_new = trader_specific_metrics['PnL_New']
            keep_human_num_transactions = max(trader_specific_metrics['Num_Sell'] , trader_specific_metrics['Num_Buy'])
            keep_penalty_original = trader_specific_metrics['Penalty_Original']
            keep_penalty_new = trader_specific_metrics['Penalty_New']

            keep_remaining_trades = trader_specific_metrics['Remaining_Trades']
            human_vwap_buy = np.mean(trader_specific_metrics['Prices_Buy']) if trader_specific_metrics['Prices_Buy'] else 0
            human_vwap_sell = np.mean(trader_specific_metrics['Prices_Sell']) if trader_specific_metrics['Prices_Sell'] else 0

            if keep_human_num_transactions == 0:
                keep_human_pnl_original_per_transaction = 0
                keep_human_pnl_new_per_transaction = 0
            else:
                keep_human_pnl_original_per_transaction = np.round(keep_human_pnl_original / keep_human_num_transactions,3)
                keep_human_pnl_new_per_transaction = np.round(keep_human_pnl_new / keep_human_num_transactions,3)
        else:
            human_id = 'no_human_'
            keep_human_pnl_original = np.nan
            keep_human_pnl_new = np.nan
            keep_human_num_transactions = np.nan
            keep_human_pnl_original_per_transaction = np.nan
            keep_human_pnl_new_per_transaction = np.nan
            keep_penalty_original = np.nan
            keep_penalty_new = np.nan
            human_vwap_buy = np.nan
            human_vwap_sell = np.nan
            keep_remaining_trades = np.nan

        if informed_id is not None:
            informed_machine_specific_metrics = all_metrics[informed_id]
            informed_machine_vwap = informed_machine_specific_metrics['VWAP']
            informed_machine_slippage = informed_machine_specific_metrics['Slippage']
            informed_machine_scaled_slippage = informed_machine_specific_metrics['Scaled_Slippage']
            informed_machine_trades = informed_machine_specific_metrics['Trades']
        else:
            informed_machine_specific_metrics = np.nan
            informed_machine_vwap = np.nan
            informed_machine_slippage = np.nan
            informed_machine_scaled_slippage = np.nan
            informed_machine_trades = np.nan

        keep_initial_midprice = all_metrics['Initial_Midprice']
        keep_last_midprice = all_metrics['Last_Midprice']
        #keep_remaining_trades = trader_specific_metrics['Remaining_Trades']
        #human_vwap_buy = np.mean(trader_specific_metrics['Prices_Buy']) if trader_specific_metrics['Prices_Buy'] else 0
        #human_vwap_sell = np.mean(trader_specific_metrics['Prices_Sell']) if trader_specific_metrics['Prices_Sell'] else 0

        new_row = pd.DataFrame({'Trader': [human_id[:-1]], 'Market': [market_id],
                                'Informed_Direction': informed_direction[index],
                                'Informed_Passive': informed_passive[index],
                                'Informed_Participation_Rate': informed_par_rate[index],
                                'PnL_Original': [keep_human_pnl_original],
                                'PnL_New': [keep_human_pnl_new],
                                'PnL_Original_per_transaction': [keep_human_pnl_original_per_transaction],
                                'PnL_New_per_transaction': [keep_human_pnl_new_per_transaction],
                                'Penalty_Original': [keep_penalty_original],
                                'Penalty_New': [keep_penalty_new],
                                'Initial_Midprice': [keep_initial_midprice],
                                'Last_Midprice': [keep_last_midprice],
                                'Informed_Machine_VWAP' : [informed_machine_vwap],
                                'Informed_Machine_Slippage' : [informed_machine_slippage],
                                'Informed_Machine_Scaled_Slippage': [informed_machine_scaled_slippage],
                                'Informed_Machine_Trades': [informed_machine_trades],
                                'Human_VWAP_Buy': [human_vwap_buy],
                                'Human_Rem_Trades' : [keep_remaining_trades],
                                'Human_VWAP_Sell': [human_vwap_sell],
                                })


        day_statistics = pd.concat([day_statistics, new_row], ignore_index=True)

day_statistics_sorted = day_statistics.sort_values(by=['Trader','Market'])
#filtered_df = day_statistics_sorted.groupby('Trader').apply(lambda group: group.iloc[1:]).reset_index(drop=True)
print(day_statistics_sorted)

save_dir = os.path.join(BASE_DIR, folders[0], DAYSTATS_SUBFOLDER)
os.makedirs(save_dir, exist_ok=True)

save_file_path = os.path.join(save_dir, f'all_{date_of_session}.csv')
day_statistics_sorted.to_csv(save_file_path, index=False)
day_statistics_sorted.to_csv(save_file_path, index=False)
# print(f"File saved to {save_file_path}")
