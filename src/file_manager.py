import pandas as pd
import os
import logging
from src.config import CURRENT_FILE, CHANGED_FILE, NEWLY_CHANGED_FILE

'''
load_previous_snapshot() - read previous snapshot 
write_current_snapshot() - write current snapshot to csv file
write_changed_snapshot() - write all updated status (after comparing) snapshot to csv file
append changes - write all newly changed status (after comparing) snapshot to csv file
'''

logging.basicConfig(level=logging.INFO)

def load_previous_snapshot():       #this one to compare, any updated status
    """
    Load previous snapshot, returning empty dict if file is missing, empty, or corrupt.
    """
    
    #Check if the file is empty
    if os.path.getsize(CURRENT_FILE) == 0:
        logging.warning(f"{CURRENT_FILE} exists but is empty. This is the first run of the data.")
        return {}
    
    try: 
        df = pd.read_csv(CURRENT_FILE)
        # Ensure required columns exist. safety check 
        if "flight_id" not in df.columns or "status" not in df.columns:
            logging.warning(f"{CURRENT_FILE} is missing required columns.")
            return {}
        # Convert to dict: flight_id -> status
        return dict(zip(df["flight_id"], df["status"]))
    except (pd.errors.EmptyDataError, pd.errors.ParserError) as e:
        logging.warning(f"Failed to read {CURRENT_FILE}: {e}. No previous data due to firt run.")
        return {}

def write_current_snapshot(flights_df, target_date):
    """Only write the snapshot if the DataFrame has data."""
    if flights_df.empty:
        logging.warning("Skipping snapshot write: DataFrame is empty.")
        return
    flights_df.to_csv(f"past_data/current_flights_{target_date}.csv", index=False)
    flights_df.to_csv(f"{CURRENT_FILE}", index=False)
    
    #console output 
    print("="*40)
    print("Current flights snapshot:")
    print("="*40)
    with pd.option_context(
        'display.max_columns', None,       # Show all columns
        'display.width', None,              # Auto-detect console width
        'display.max_colwidth', None,       # Show full content of each cell
        'display.max_rows', None            # Show all rows (or set a limit e.g., 20)
    ):
        print(flights_df)

def write_changed_snapshot(flights_df, target_date):
    if flights_df.empty:
        logging.warning("Skipping changed snapshot write: DataFrame is empty.")
        return
    flights_df[flights_df["status"].str.lower().isin(["delayed", "cancelled"])].to_csv(f"past_data/changed_flights_{target_date}.csv", index=False)
    flights_df[flights_df["status"].str.lower().isin(["delayed", "cancelled"])].to_csv(f"{CHANGED_FILE}", index=False)
    print("=" * 40)
    print("Delayed/cancelled flights snapshot :")
    print("=" * 40)
    with pd.option_context(
        'display.max_columns', None,       # Show all columns
        'display.width', None,              # Auto-detect console width
        'display.max_colwidth', None,       # Show full content of each cell
        'display.max_rows', None            # Show all rows (or set a limit e.g., 20)
    ):
        print(flights_df[flights_df["status"].str.lower().isin(["delayed", "cancelled"])])
    

def append_changes(new_change_records):     #receive flights_id and status key-value pair 
    """
    Overwrites CHANGED_FILE with all records that have status 'delayed' or 'cancelled'
    from the current run. No history is kept – the file is replaced entirely.
    """

    #overwrite into an empty file if no new records, output nothing on the console
    if not new_change_records:
        df_new = pd.DataFrame(new_change_records)
        df_new.to_csv(NEWLY_CHANGED_FILE, index=False)  
        return

    # Convert new records to DataFrame
    df_new = pd.DataFrame(new_change_records)

    '''
    # --- Safety filter: keep only delayed or cancelled ---
    safety filter no need because new_change_records is already filtered, only consist delayed and cancelled
    if "status" in df_new.columns:
        df_new = df_new[df_new["status"].str.lower().isin(["delayed", "cancelled"])]
    '''

    # --- Overwrite the file directly ---
    try: 
        df_new.to_csv(NEWLY_CHANGED_FILE, index=False)
    except Exception as e: #catch the exception as e
        logging.error(f"Failed to write {NEWLY_CHANGED_FILE}: {e}")
        return

    print("=" * 40)
    print("Newly fetch delayed/cancelled flight status:")
    print("=" * 40)
    with pd.option_context(
        'display.max_columns', None,       # Show all columns
        'display.width', None,              # Auto-detect console width
        'display.max_colwidth', None,       # Show full content of each cell
        'display.max_rows', None            # Show all rows (or set a limit e.g., 20)
    ):
        print(df_new)

#already append and won't override the header 
def append_to_csv(new_data, csv_file="/Users/fionaleong/HKIA_flight_monitor/data/HKIA_merged.csv"):
    """
    Append new data to the CSV file.
    """
    try:
        df_new = pd.DataFrame(new_data)

        #if starting new file, then must write header 
        if os.path.getsize(csv_file) == 0:
            df_new.to_csv(csv_file, mode='a', header=True, index=False) #append and write the header
        else:
            df_new.to_csv(csv_file, mode='a', header=False, index=False) #append and dont write the header
    except Exception as e:
        logging.error(f"Failed to append to {csv_file}: {e}")
