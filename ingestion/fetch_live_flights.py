import datetime
import os
import argparse
from datetime import datetime, timedelta, timezone
from textwrap import indent

import requests
import pandas as pd
from dotenv import load_dotenv
import json

from google.cloud import storage

load_dotenv()

API_KEY = os.environ.get("AERODATABOX_API_KEY")
API_HOST = "aerodatabox.p.rapidapi.com"
BASE_URL = "https://aerodatabox.p.rapidapi.com/flights/airports/iata"

RAW_DATA_DIR = "/Users/ming/Documents/Projects/flight-delay-pipeline/live_raw_data"

DEFAULT_AIRPORTS = ["ATL"]

HEADERS = {
    "X-RapidAPI-Key": API_KEY,
    "X-RapidAPI-Host": API_HOST,
}

# maps AeroDataBoxs nested JSON fields to the flat column names used by the bts data model
# sources land in a consistent shape.
def flatten_flight_data(record: dict, airport: str, direction: str) -> dict:
    departure_flight = record.get('departure') or {}
    arrival_flight = record.get('arrival') or {}
    
    def get_time(block, key):
        subBlock = (block or {}).get(key)
        return subBlock.get('local') if subBlock else None
    
    return {
        "FlightDate": (get_time(departure_flight, "scheduledTime") or "")[:10] or None,
        "Reporting_Airline": (record.get("airline") or {}).get("iata"),
        "FlightNumber": record.get("number"),
        "Origin": (departure_flight.get("airport") or {}).get("iata") or (airport if direction == "departure" else None),
        "Dest": (arrival_flight.get("airport") or {}).get("iata") or (airport if direction == "arrival" else None),
        "CRSDepTime": get_time(departure_flight, "scheduledTime"),
        "DepTime": get_time(departure_flight, "runwayTime") or get_time(departure_flight, "revisedTime"),
        "CRSArrTime": get_time(arrival_flight, "scheduledTime"),
        "ArrTime": get_time(arrival_flight, "runwayTime") or get_time(arrival_flight, "revisedTime"),
        "FlightStatus": record.get("status"),
        "Direction": direction,
    }
    
def fetch_window(airport: str, from_local: str, to_local: str) -> list:
    url = f"{BASE_URL}/{airport}/{from_local}/{to_local}"
    params = {
        "withLeg": "true",
        "direction": "Both",
        "withCancelled": "true",
        "withCodeshared": "false",
        "withCargo": "false",
        "withPrivate": "false",
    }
    response = requests.get(url, headers=HEADERS, params=params, timeout=60)
    response.raise_for_status()
    payload = response.json()
    
    print(json.dumps(payload.get('departures', [])[0], indent=2))
 
    records = []
    for flight in payload.get("departures", []):
        records.append(flatten_flight_data(flight, airport, "departure"))
    for flight in payload.get("arrivals", []):
        records.append(flatten_flight_data(flight, airport, "arrival"))
    return records

def fetch_day(date_str: str, airports: list) -> pd.DataFrame:
    all_records = []
    for airport in airports:
        # each call limited to 12-hour window
        for start_hour, end_hour in [("00:00", "11:59"), ("12:00", "23:59")]:
            from_local = f"{date_str}T{start_hour}"
            to_local = f"{date_str}T{end_hour}"
            try:
                all_records.extend(fetch_window(airport, from_local, to_local))
            except requests.HTTPError as exc:
                print(f"  Failed for {airport} {from_local}-{to_local}: {exc}")
    return pd.DataFrame(all_records)

# load live data as parquet to directory
def land_parquet_gcs(df: pd.DataFrame, date_str, bucket_name="flight-delay-raw"):
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    blob = bucket.blob(f"raw/live/flights_live_{dt.year}_{dt.month:02d}/flights_{date_str}.parquet")
    blob.upload_from_string(df.to_parquet(index=False), content_type="application/octet-stream")
    
    print(f"Wrote {len(df):,} rows -> {bucket_name}")
    
    
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--date",
        default=(datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d"),
        help="YYYY-MM-DD, defaults to yesterday",
    )
    parser.add_argument(
        "--airports",
        default=",".join(DEFAULT_AIRPORTS),
        help="Comma-separated IATA airport codes",
    )
    args = parser.parse_args()
 
    airports = [a.strip().upper() for a in args.airports.split(",")]
    df = fetch_day(args.date, airports)
    land_parquet_gcs(df, args.date)
 
 
if __name__ == "__main__":
    main()