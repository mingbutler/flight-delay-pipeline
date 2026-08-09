import io
import os

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

GCS_BUCKET = os.environ.get("GCS_BUCKET", "flight-delay-raw")

PAST_MONTHS_DOWNLOADED = set()

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
        
        if (year, month) in PAST_MONTHS_DOWNLOADED:
            raise FileExistsError(f"Month {year}-{month:02d} already downloaded.")
        
        if check_url_exists(url):
            print("FOUND!")
            PAST_MONTHS_DOWNLOADED.add((year, month))
            return url, year, month
        
        print(f"Month of {month} not available yet.")
        
        if month == 1:
            month = 12
            year -= 1
        else:
            month -= 1
    
    raise FileNotFoundError("Could not locate any recent BTS zip files. Please check your network connection.")

COLUMNS_KEEP = [
    "FlightDate", "Reporting_Airline", "Flight_Number_Reporting_Airline", "Origin", "Dest",
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
        raise RuntimeError(f"No recent BTS zip files found: {e}") from e
    
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
        raise RuntimeError(f"Error during download: {e}") from e

def land_parquet_gcs(df: pd.DataFrame, year, month, bucket_name=GCS_BUCKET):  
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(f"raw/bts/year={year}/month={month:02d}/flights.parquet")
    blob.upload_from_string(df.to_parquet(index=False), content_type="application/octet-stream")
     
    print(f"Wrote {len(df):,} rows -> {bucket_name}")
    
def run():
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
    run()