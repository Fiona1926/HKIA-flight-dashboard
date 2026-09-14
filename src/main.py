import logging
import argparse #testing to fetch specific date 
from datetime import datetime, date
#import all functions from different modules
from src.api_client import fetch_flights
from src.data_processor import process_flights
from src.file_manager import write_current_snapshot, write_changed_snapshot, append_changes, append_to_csv

logging.basicConfig(level=logging.INFO) #basic logging from different libraries

def run(target_date=date.today(), cargo= 'true', arrival='false'):   

    '''
    by default, cargo departure today
    '''

    logging.info("Starting flight data extraction...")
    try:
        flights = fetch_flights(target_date, cargo, arrival) #change to fetch_arrival_flights() for arrivals
        if not flights:     #raise a warning if no response from API
            logging.warning("No flights returned from API.")
            return

        full_df, changes = process_flights(flights)     #full df and newly status changes, utilized load_previous_snapshot

      
        write_current_snapshot(full_df, target_date)         #write full snapshot of current flight status
        write_changed_snapshot(full_df, target_date)         #write full snapshot of changed flights (delayed/cancelled)
        append_changes(changes)               #write only newly changed status flights, say new cancellation or delayed
        if (target_date <date.today()):
            append_to_csv(full_df)                #append to csv for historical data
        else:
            append_to_csv(full_df, "/Users/fionaleong/HKIA_flight_monitor/data/HKIA_upcoming.csv" )     #append to temporary storage
        #no duplication check 

        logging.info(f"Saved {len(full_df)} flights; {len(changes)} new delayed/cancelled flights.")
    except Exception as e:
        logging.error(f"Run failed: {e}")
'''
if date is specified fetch API from that specific date
else fetch API from today
'''
if __name__ == "__main__":      #this shall be the main program 
    parser = argparse.ArgumentParser()
    parser.add_argument('--date', help='Date in YYYY-MM-DD format (defaults to today)')
    parser.add_argument('--cargo', type= str,choices= ['true','false'])
    parser.add_argument('--arrival', type= str,  choices= ['true','false'])
    args = parser.parse_args()

    if args.date:
        target_date = datetime.strptime(args.date, "%Y-%m-%d").date()   
    else: 
        target_date = date.today()

    cargo_flag = args.cargo 
    arrival_flag = args.arrival

    # Now call your run() function with the date
    run(target_date, cargo_flag, arrival_flag)