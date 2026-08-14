import os

import requests
import pandas as pd
from dotenv import load_dotenv

from google.cloud import storage
from airflow.models import Variable

load_dotenv()

GCS_BUCKET = os.environ.get("GCS_BUCKET", "flight-delay-raw")

API_KEY = Variable.get("AERODATABOX_API_KEY")
API_HOST = "aerodatabox.p.rapidapi.com"
BASE_URL = "https://aerodatabox.p.rapidapi.com/flights/airports/iata"

DEFAULT_AIRPORTS = ["ATL"]

def _get_headers() -> dict:
    api_key = Variable.get("AERODATABOX_API_KEY")
    return {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": API_HOST,
    }

# maps AeroDataBoxs nested JSON fields to the flat column names used by the bts data model
# sources land in a consistent shape.
def flatten_flight_data(record, airport, direction):
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
    
def fetch_window(airport, from_local, to_local):
    url = f"{BASE_URL}/{airport}/{from_local}/{to_local}"
    params = {
        "withLeg": "true",
        "direction": "Both",
        "withCancelled": "true",
        "withCodeshared": "false",
        "withCargo": "false",
        "withPrivate": "false",
    }
    response = requests.get(url, headers=_get_headers(), params=params, timeout=60)
    response.raise_for_status()
    payload = response.json()
 
    records = []
    for flight in payload.get("departures", []):
        records.append(flatten_flight_data(flight, airport, "departure"))
    for flight in payload.get("arrivals", []):
        records.append(flatten_flight_data(flight, airport, "arrival"))
    return records

def fetch_day(date_str, airports):
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
def land_parquet_gcs(df, date_str, bucket_name=GCS_BUCKET):
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    
    blob = bucket.blob(f"raw/live/dt={date_str}/flights.parquet")
    blob.upload_from_string(df.to_parquet(index=False), content_type="application/octet-stream")
    
    print(f"Wrote {len(df):,} rows -> {bucket_name}")
    
    
def run(date_str, airports):
    df = fetch_day(date_str, airports)
    land_parquet_gcs(df, date_str)
 
 
# if __name__ == "__main__":
#     run()