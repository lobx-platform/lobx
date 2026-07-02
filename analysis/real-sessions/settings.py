"""
Central configuration for the Real Sessions log-analysis pipeline.

EDIT ONLY THIS FILE between sessions. Point BASE_DIR at the folder that
contains the session subfolder (the one holding Logfiles/, Order_Books/,
DayStatistics/), choose which subfolder + session date to analyse, then run:

    python main.py

The analysis scripts (generate_statistics_by_folder.py, analysis.py,
order_book.py) read everything below from here, so nothing else needs to
change when you analyse a new session.
"""
import os

# === EDIT THESE FOR EACH SESSION ===========================================

# Folder that contains the session subfolder (FOLDER below).
# Examples:
#   live Dropbox mount (make the session folder "available offline" first):
#       BASE_DIR = os.path.expanduser(
#           '~/Dropbox/InformationDisseminatationProject/Real Sessions Udine')
#   a local folder you copied a session's data into:
#       BASE_DIR = os.path.join(os.path.dirname(__file__), '_local_data')
BASE_DIR = os.path.expanduser(
    '~/Dropbox/Accademic/InformationDisseminatationProject/ResultsExperiments/Real_Sessions_Siena_20260622')



# Which session subfolder to analyse, and the date used in file names
# (all_<DATE>.csv, filtered_<DATE>.csv, ...).
FOLDER = 'Treatments'
DATE = '20260622'

CCY = 'Euro'
CONVERSION_RATE = 2 #liras per unit of CCY local currency (e.g. GBP or EUR)


# Subfolder names inside FOLDER. These vary by session — check on disk.
LOGFILES_SUBFOLDER = 'Logfiles'        # raw .log files
DAYSTATS_SUBFOLDER = 'Daystatistics'   # all aggregate outputs are written here
ORDER_BOOKS_SUBFOLDER = 'Order_Books'  # per-market order-book .csv files (built by stage 1)

# Session metadata. Only used to label columns in all_<DATE>.csv (one entry
# per folder in FOLDERS below); does not affect any computation.
INFORMED_PASSIVE = ['Mixed']
INFORMED_PAR_RATE = ['Mixed']

# === DERIVED (no need to edit) =============================================
FOLDERS = [FOLDER]
FOLDER_DIR = os.path.join(BASE_DIR, FOLDER)
LOGFILES_DIR = os.path.join(FOLDER_DIR, LOGFILES_SUBFOLDER)
DAYSTATS_DIR = os.path.join(FOLDER_DIR, DAYSTATS_SUBFOLDER)
ORDER_BOOKS_DIR = os.path.join(FOLDER_DIR, ORDER_BOOKS_SUBFOLDER)
