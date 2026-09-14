#!/bin/bash

# Navigate to your project root
cd /Users/fionaleong/HKIA_flight_monitor || exit 1

#remove old upcoming file and create new ones 
rm /Users/fionaleong/HKIA_flight_monitor/data/HKIA_upcoming.csv
touch /Users/fionaleong/HKIA_flight_monitor/data/HKIA_upcoming.csv

# Create logs folder if it doesn't exist
mkdir -p back_logs

# ================= CONFIGURE YOUR DATE RANGE =================

#date range for backfill, for all available dates
START_DATE=$(date -v-1d +%Y-%m-%d) #change this to your earliest desired date
END_DATE=$(date -v+2d +%Y-%m-%d) 

# =============================================================
# Convert dates to epoch seconds (macOS compatible)
start_epoch=$(date -j -f "%Y-%m-%d" "$START_DATE" +%s)
end_epoch=$(date -j -f "%Y-%m-%d" "$END_DATE" +%s)

current_epoch=$start_epoch 

echo "========================================" | tee -a "back_logs/backfill.log"
echo "$(date): Starting backfill from $START_DATE to $END_DATE" | tee -a "back_logs/backfill.log"
echo "========================================" | tee -a "back_logs/backfill.log"

# Python interpreter path
PYTHON_CMD="/Users/fionaleong/HKIA_flight_monitor/.venv_HKIA/bin/python"

# cargo arrival flag (make sure no spacing)
FLAG_COMBOS=(
    "true true"
    "true false"
)


while [[ $current_epoch -le $end_epoch ]]; do

    
    # Convert epoch back to YYYY-MM-DD
    current_date=$(date -j -f "%s" "$current_epoch" +%Y-%m-%d)
    BACKLOG_FILE="back_logs/run_${current_date}.backlog"
    current_date=$(date -j -f "%s" "$current_epoch" +%Y-%m-%d)

    # Inner loop over flag combinations
    for combo in "${FLAG_COMBOS[@]}"; do
        # Split the combo into cargo and arrival
        CARGO_FLAG=$(echo "$combo" | cut -d' ' -f1)
        ARRIVAL_FLAG=$(echo "$combo" | cut -d' ' -f2)

        echo "$(date): Running src.main for ${current_date} with cargo=${CARGO_FLAG} arrival=${ARRIVAL_FLAG}" | tee -a "back_logs/backfill.log"

        $PYTHON_CMD -m src.main --date "$current_date" --cargo "$CARGO_FLAG" --arrival "$ARRIVAL_FLAG" >> "$BACKLOG_FILE" 2>&1

        exit_code=$?
        if [ $exit_code -eq 0 ]; then
            echo "$(date): Successfully processed ${current_date} (cargo=${CARGO_FLAG}, arrival=${ARRIVAL_FLAG})" | tee -a "back_logs/backfill.log"
        else
            echo "$(date): Failed to process ${current_date} (cargo=${CARGO_FLAG}, arrival=${ARRIVAL_FLAG}) (Exit code: ${exit_code})" | tee -a "back_logs/backfill.log"
        fi

        # Brief pause between combos (optional)
        sleep 1
    done

    # Move to the next day
    current_epoch=$((current_epoch + 86400))
done


echo "========================================" | tee -a "back_logs/backfill.log"
echo "$(date): Backfill completed!" | tee -a "back_logs/backfill.log"
echo "========================================" | tee -a "back_logs/backfill.log"