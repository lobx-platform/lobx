import numpy as np
import pandas as pd
import os
from datetime import datetime
import random

def remove_first_market(df_i):
    df_i= df_i.loc[df_i['Id'] != 0].reset_index(drop=True)
    return df_i

from settings import BASE_DIR, FOLDER, DATE, DAYSTATS_SUBFOLDER

pathname = BASE_DIR
folder = FOLDER
date_of_session = DATE
file = 'all_' + date_of_session + '.csv'

filename1 = pathname + '/' + folder + '/' + DAYSTATS_SUBFOLDER + '/' + file
#filename2 = pathname + '/' + folder + '/' +  'Prolific_ID_Exclude.csv'


df = pd.read_csv(filename1, header=0)
df['Session'] = df['Market'].str.rsplit('_', n=1).str[0]
df['Id'] = df['Market'].str.split('_').str[-1].astype(int)

#df_to_exclude = pd.read_csv(filename2, header=0)


#df_filtered = df[~df['Trader'].isin(df_to_exclude['Trader'])]

df_filtered = df
# pandas-version-stable equivalent of groupby('Session').apply(remove_first_market):
# Id is the per-session market index, so dropping Id==0 drops each session's first market.
df_filtered_final = df_filtered[df_filtered['Id'] != 0].sort_values(by=['Session', 'Id']).reset_index(drop=True)

save_file_path = pathname + '/' + folder + '/' + DAYSTATS_SUBFOLDER + '/' + f'filtered_{date_of_session}.csv'

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
save_file_path = pathname + '/' + folder + '/' + DAYSTATS_SUBFOLDER + '/' + f'payment_{date_of_session}.csv'
df_filtered_final_payment.to_csv(save_file_path, index=False)
