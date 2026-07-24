import os 
import io
import sys

from zipfile import ZipFile
from datetime import datetime

import requests
import pandas as pd
from dateutil.relativedelta import relativedelta

from google.cloud import storage

'''
- downloads pre-zipped data files from the US DOT Bureau of
Transportation Statistics (BTS) "Airline On-Time Performance"
'''

RAW_DATA_DIR = "/Users/ming/Documents/Projects/flight-delay-pipeline/bts_data"

def check_url_exists(url):
    try:
        response = requests.head(url, allow_redirects=True, timeout=10)
        
        return response.status_code == 200 and 'html' not in response.headers.get('content-type', '')
    except requests.RequestException:
        return False
    
def get_latest_available_month():
    current_date = datetime.now()
    year = current_date.year
    month = current_date.month
    
    print("Searching for the most recent available BTS dataset...")
    
    # look back 6 months for most recent upload
    for _ in range(6):
        url = f"https://transtats.bts.gov/PREZIP/On_Time_Reporting_Carrier_On_Time_Performance_1987_present_{year}_{month}.zip"
        print(f"Checking {year}-{month:02d}... ", end="")
        
        if check_url_exists(url):
            print("FOUND!")
            return url, year, month
        
        print(f"Month of {month} not available yet.")
        
        if month == 1:
            month = 12
            year -= 1
        else:
            month -= 1
    
    raise FileNotFoundError("Could not locate any recent BTS zip files. Please check your network connection.")

COLUMNS_KEEP = [
    "FlightDate", "Reporting_Airline", "Origin", "Dest",
    "CRSDepTime", "DepTime", "DepDelayMinutes",
    "CRSArrTime", "ArrTime", "ArrDelayMinutes",
    "Cancelled", "CancellationCode", "Diverted",
    "Distance",
    "CarrierDelay", "WeatherDelay", "NASDelay",
    "SecurityDelay", "LateAircraftDelay",
]

def download_month():
    # find latest month url
    try:
        url, year, month = get_latest_available_month()
    except FileNotFoundError as e:
        print(e)
        sys.exit(1)
    
    # download with progress bar
    print(f"\nDownloading: {url}")
    try:
        response = requests.get(url, stream=True, timeout=120)
        response.raise_for_status()
        
        with ZipFile(io.BytesIO(response.content)) as file:
            csv_file = next(n for n in file.namelist() if n.endswith('.csv'))
            with file.open(csv_file) as f:
                df = pd.read_csv(f, usecols=lambda c: c in COLUMNS_KEEP, low_memory=False)
        print("\nDownload complete.")
        return df, year, month

    except requests.RequestException as e:
        print(f"Error during download: {e}")
        sys.exit(1)

def land_parquet_gcs(df: pd.DataFrame, year, month, bucket_name="flight-delay-raw"):  
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(f"raw/bts/bts_ontime_{year}_{month:02d}/flights.parquet")
    blob.upload_from_string(df.to_parquet(index=False), content_type="application/octet-stream")
     
    print(f"Wrote {len(df):,} rows -> {bucket_name}")
    
def main():
    try:
        df, year, month = download_month()
        land_parquet_gcs(df, year, month) 
    except requests.HTTPError as e:
        print(
                f"  Failed for {year}-{month:02d}: {e}. "
                "If this is the most recent month, BTS may not have published "
                "it yet -- they typically lag ~6-8 weeks behind month end."
            )
            
if __name__ == "__main__":
    main()