"""
Run the Real Sessions analysis pipeline end to end, in order:

    1. generate_statistics_by_folder.py   raw Logfiles  -> all_<DATE>.csv
    2. analysis.py                         all_<DATE>    -> filtered_<DATE>.csv, payment_<DATE>.csv
    3. order_book.py                       filtered_<DATE> + Order_Books -> <FOLDER>_markets.csv, <FOLDER>_OB.csv

Configure everything in settings.py first, then:

    python main.py
"""
import os
import runpy

import settings

SCRIPTS = [
    'generate_statistics_by_folder.py',
    'analysis.py',
    'order_book.py',
    'order_book_detailed.py',
]

if __name__ == '__main__':
    here = os.path.dirname(os.path.abspath(__file__))
    print(f"FOLDER = {settings.FOLDER}   DATE = {settings.DATE}")
    print(f"BASE_DIR = {settings.BASE_DIR}")
    for script in SCRIPTS:
        print(f"\n===== running {script} =====", flush=True)
        runpy.run_path(os.path.join(here, script), run_name='__main__')
    print(f"\nDone. Outputs written to: {settings.DAYSTATS_DIR}")
