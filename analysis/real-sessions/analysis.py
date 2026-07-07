import numpy as np
import pandas as pd
import os
from datetime import datetime
import random

def remove_first_market(df_i):
    df_i= df_i.loc[df_i['Id'] != 0].reset_index(drop=True)
    return df_i

from settings import BASE_DIR, FOLDER, DATE, DAYSTATS_SUBFOLDER, CCY,CONVERSION_RATE

pathname = BASE_DIR
folder = FOLDER
date_of_session = DATE

RANDOM_STATE = 123

# Per-market payment cap in CCY (issue #78): was 10, now set very high to
# effectively disable it while retaining the capping code path.
PAYMENT_CAP_CCY = 1_000_000

save_dir = os.path.join(pathname, folder, DAYSTATS_SUBFOLDER)
os.makedirs(save_dir, exist_ok=True)

file = f'all_{date_of_session}.csv'
filename1 = os.path.join(save_dir, file)

#filename2 = pathname + '/' + folder + '/' +  'Prolific_ID_Exclude.csv'


df = pd.read_csv(filename1, header=0)
df['Session'] = df['Market'].str.rsplit('_', n=1).str[0]

#old does not extract the correct market ID
#df['Id'] = df['Market'].str.split('_').str[-1].astype(int)
df['Id'] = df['Market'].str.extract(r'_M(\d+)_')[0].astype(int)


#df_to_exclude = pd.read_csv(filename2, header=0)


#df_filtered = df[~df['Trader'].isin(df_to_exclude['Trader'])]

df_filtered = df

# Exclude training market M0
df_filtered_final = (
    df_filtered[df_filtered['Id'] != 0]
    .sort_values(by=['Trader', 'Id'])
    .reset_index(drop=True)
)


save_file_path = os.path.join(save_dir, f'filtered_{date_of_session}.csv')
#save_file_path = pathname + '/' + folder + '/' + DAYSTATS_SUBFOLDER + '/' + f'filtered_{date_of_session}.csv'

NON_HUMAN_LABEL = 'no_human'

def replace_nohuman(group):
    # extract human names (LAB_*)
    humans = group.loc[group['Trader'] != NON_HUMAN_LABEL, 'Trader'].unique()

    # only act if at least one human exists
    if len(humans) > 0:
        replacement = humans[0]  # or random.choice(humans)

        group.loc[group['Trader'] == NON_HUMAN_LABEL, 'Trader'] = replacement

    return group

# pandas-version-stable equivalent of groupby('Trader').apply(replace_nohuman):
# In the current Real Sessions format, payment is participant-level,
# so we keep no_human rows only if no participant can be mapped.
_session_human = (
    df_filtered_final[df_filtered_final['Trader'] != NON_HUMAN_LABEL]
    .groupby('Trader')['Trader']
    .first()
)

_nohuman_mask = df_filtered_final['Trader'] == NON_HUMAN_LABEL
df_filtered_final.loc[_nohuman_mask, 'Trader'] = (
    df_filtered_final.loc[_nohuman_mask, 'Trader']
    .map(_session_human)
    .fillna(NON_HUMAN_LABEL)
)


df_filtered_final.to_csv(save_file_path, index=False)

# Payment = average of max(per-market earnings, 0) over all non-practice
# markets (issue #78). This replaces the random selection of a single paying
# market and must stay in sync with Accumulated_Reward on the platform
# (back/api/routes/trading.py).
# Old behaviour, kept for reference:
# df_filtered_final_payment = (
#     df_filtered_final[df_filtered_final['Trader'] != NON_HUMAN_LABEL]
#     .groupby('Trader', group_keys=False)
#     .sample(n=1, random_state=RANDOM_STATE )
#     .reset_index(drop=True)
# )
# df_filtered_final_payment[CCY] = (
#     df_filtered_final_payment['PnL_Original'] / CONVERSION_RATE
# ).clip(lower=0, upper=10)
df_payment_base = df_filtered_final[
    df_filtered_final['Trader'] != NON_HUMAN_LABEL
].copy()
df_payment_base[CCY] = (
    df_payment_base['PnL_Original'] / CONVERSION_RATE
).clip(lower=0, upper=PAYMENT_CAP_CCY)

df_filtered_final_payment = (
    df_payment_base
    .groupby('Trader', as_index=False)
    .agg(**{'Markets': ('Id', 'nunique'), CCY: (CCY, 'mean')})
)


save_file_path = os.path.join(save_dir, f'payment_{date_of_session}.csv')
#save_file_path = pathname + '/' + folder + '/' + DAYSTATS_SUBFOLDER + '/' + f'payment_{date_of_session}.csv'


df_filtered_final_payment.to_csv(save_file_path, index=False)


"""
#this does not appear to 
# pandas-version-stable equivalent of groupby('Session').apply(remove_first_market):
# Id is the per-session market index, so dropping Id==0 drops each session's first market.
df_filtered_final = df_filtered[df_filtered['Id'] != 0].sort_values(by=['Session', 'Id']).reset_index(drop=True)


save_file_path = os.path.join(save_dir, f'filtered_{date_of_session}.csv')
#save_file_path = pathname + '/' + folder + '/' + DAYSTATS_SUBFOLDER + '/' + f'filtered_{date_of_session}.csv'

NON_HUMAN_LABEL = 'no_human'

def replace_nohuman(group):
    # extract human names (LAB_*)
    humans = group.loc[group['Trader'] != NON_HUMAN_LABEL, 'Trader'].unique()

    # only act if at least one human exists
    if len(humans) > 0:
        replacement = humans[0]  # or random.choice(humans)

        group.loc[group['Trader'] == NON_HUMAN_LABEL, 'Trader'] = replacement

    return group

# pandas-version-stable equivalent of groupby('Session').apply(replace_nohuman):
# within each session, relabel 'no_human' rows with that session's (first) human trader.
_session_human = (df_filtered_final[df_filtered_final['Trader'] != NON_HUMAN_LABEL]
                  .groupby('Session')['Trader'].first())
_nohuman_mask = df_filtered_final['Trader'] == NON_HUMAN_LABEL
df_filtered_final.loc[_nohuman_mask, 'Trader'] = (
    df_filtered_final.loc[_nohuman_mask, 'Session'].map(_session_human).fillna(NON_HUMAN_LABEL)
)


df_filtered_final.to_csv(save_file_path, index=False)

df_filtered_final_payment = df_filtered_final.loc[df_filtered_final.Id == 5].groupby('Session').first().reset_index()[['Session', 'Trader' ,'PnL_Original']]
df_filtered_final_payment['Euro'] = (df_filtered_final_payment['PnL_Original'] / 2).clip(lower=0, upper=10)


save_file_path = os.path.join(save_dir, f'payment_{date_of_session}.csv')
#save_file_path = pathname + '/' + folder + '/' + DAYSTATS_SUBFOLDER + '/' + f'payment_{date_of_session}.csv'


df_filtered_final_payment.to_csv(save_file_path, index=False)
"""
