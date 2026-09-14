# HKIA Data & Dashboard

A real-time flight monitoring and data pipeline tool that fetches flight information from the **Hong Kong International Airport (HKIA) API** and visualizes it using python's **Streamlit** framework.

## 📂 Project Structure

```text
HKIA_flight_monitor/
.
├── __init__.py
├── back_logs
├── data
│   ├── changed_flights.csv
│   ├── current_flights.csv
│   ├── HKIA_merged.csv
│   ├── newly_changed_flights.csv
│   └── online_ports.csv
├── libraries.py
├── logs
├── past_data
├── README.md
├── requirements.txt
├── scripts
│   ├── backfill_cargo.sh
│   ├── backfill.sh
│   └── run_with_log.sh
└── src
    ├── __init__.py
    ├── api_client.py
    ├── config.py
    ├── csv_analysis.py
    ├── data_processor.py
    ├── file_manager.py
    ├── main.py
    └── visuals.py
```
    
## 🚀 Getting Started

### 1. Installation
Clone the repository and install the required dependencies within your virtual environment:
```bash
pip install -r requirements.txt
```

### 2. Running the Data Pipeline
To execute the ETL process and fetch the latest data from the HKIA API, run in root folder:
```bash
python src/main.py
```

#### Command-Line Arguments
You can customize the data extraction using optional CLI flags:

* `--date`: Target a specific date in `YYYY-MM-DD` format (defaults to today).
* `--cargo`: Filter for cargo flights (`true` or `false`).
* `--arrival`: Filter for arrival flights (`true` or `false`).

#### Examples
Fetch flight data for a **specific historical date**:
```bash
python src/main.py --date 2026-09-01
```

Fetch only **cargo arrival flights** for today:
```bash
python src/main.py --cargo true --arrival true
```

### 3. Running the Historical Backfill
If you need to sync historical or future flight logs, use the provided `backfill.sh` automation script. 

These automation script already covers arrival/departure data for CARGO only.

Before running, open `scripts/backfill.sh` and modify the **START_DATE** and **END_DATE** range parameters to target your desired historical timeline:

```bash

START_DATE=\$(date -v-90d +%Y-%m-%d) 
END_DATE=\$(date -v+2d +%Y-%m-%d)   
```

Once your dates are set, give the script execution permissions and run it from your terminal in root folder :
```bash
chmod +x scripts/backfill.sh
#or get full path
chmod +x fullpath/backfill.sh

#run the script by pasting the path in your terminal
./scripts/backfill.sh
```

### 4. Launching the Streamlit Dashboard
To spin up the web-based tracking dashboard for data visualization, run:
```bash
streamlit run src/visuals.py
```
