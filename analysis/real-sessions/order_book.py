import numpy as np
import pandas as pd
import os
from datetime import datetime
import random

from settings import BASE_DIR, FOLDER, DATE, DAYSTATS_SUBFOLDER, ORDER_BOOKS_SUBFOLDER

pathname = BASE_DIR
folder = FOLDER

filename = pathname + '/' + folder + '/'+ DAYSTATS_SUBFOLDER + '/'

files = [f'filtered_{DATE}.csv']


df = pd.read_csv(filename + files[0])


order_book_markets_needed = list( df.loc[df.Trader != 'no_human']['Market'] )


order_books_folder = pathname + '/' + folder + '/' + ORDER_BOOKS_SUBFOLDER
# for file in os.listdir(order_books_folder):
#     print(file)


def pool_order_books(order_books_folder,order_book_markets_needed,filename_to_export):
  all_df = pd.DataFrame()
  for file in order_book_markets_needed:
    filename_to_read = order_books_folder + '/' + f'{file}' + '.csv'
    df = pd.read_csv(filename_to_read,header=0)
    all_df = pd.concat([all_df,df],axis=0).reset_index(drop=True)

  all_df.sort_values(by=['Trader', 'Market'], ascending=[True, True], inplace=True)
  all_df.to_csv(filename_to_export,index=False)

pool_order_books(order_books_folder,order_book_markets_needed,filename_to_export=filename + 'Udine_OB.csv')
