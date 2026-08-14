import io
import os
import tempfile
import typing
from pandas._typing import DtypeArg

from zipfile import ZipFile
from datetime import datetime

import requests
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from dateutil.relativedelta import relativedelta

from typing import List
import numpy as np

from google.cloud import storage

'''
- downloads pre-zipped data files from the US DOT Bureau of
Transportation Statistics (BTS) "Airline On-Time Performance"
'''

GCS_BUCKET = os.environ.get("GCS_BUCKET", "flight-delay-raw")


# custom exception for no new data available
class NoNewDataError(Exception):
    pass



def check_url_exists(url):
    try:
        response = requests.head(url, allow_redirects=True, timeout=10)
        
        return response.status_code == 200 and 'html' not in response.headers.get('content-type', '')
    except requests.RequestException:
        return False
    
# check with GCS if a month has already been downloaded 
def month_already_ingested(year, month, bucket_name=GCS_BUCKET):
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(f"raw/bts/year={year}/month={month:02d}/flights.parquet")
    return blob.exists()
    
def get_latest_available_month():
    current_date = datetime.now()
    year = current_date.year
    month = current_date.month
    
    print("Searching for the most recent available BTS dataset...")
    
    # look back 6 months for most recent upload
    for _ in range(6):
        print(f"Checking {year}-{month:02d}... ", end="")
        
        if month_already_ingested(year, month):
            print(f"{year}-{month:02d} already ingested, skipping.")
        else:
            url = f"https://transtats.bts.gov/PREZIP/On_Time_Reporting_Carrier_On_Time_Performance_1987_present_{year}_{month}.zip"
            if check_url_exists(url):
                print(f"FOUND new month: {year}-{month:02d}")
                return url, year, month
        
        if month == 1:
            month = 12
            year -= 1
        else:
            month -= 1
    
    raise NoNewDataError("No new BTS month available to ingest.")

COLUMNS_KEEP: List[str] = [
    "FlightDate", "Reporting_Airline", "Flight_Number_Reporting_Airline", "Origin", "Dest",
    "CRSDepTime", "DepTime", "DepDelayMinutes",
    "CRSArrTime", "ArrTime", "ArrDelayMinutes",
    "Cancelled", "CancellationCode", "Diverted",
    "Distance",
    "CarrierDelay", "WeatherDelay", "NASDelay",
    "SecurityDelay", "LateAircraftDelay",
]

DTYPE_OVERRIDES: typing.Mapping[typing.Hashable, DtypeArg] = {
    "CancellationCode": "object",   # NaN when not cancelled, 'A'/'B'/'C'/'D' when it is
    "Cancelled": "float64",
    "Diverted": "float64",
}

CHUNK_ROWS = 100_000

def download_zip_to_tempfile(url):
    # streams to disk
    fd, path = tempfile.mkstemp(suffix=".zip")

    with os.fdopen(fd, 'wb') as temp_file:
        with requests.get(url, stream=True, timeout=120) as response:
            response.raise_for_status()
            # write contents in chunks to temp file
            for chunk in response.iter_content(chunk_size=1048576):
                temp_file.write(chunk)
    return path

def csv_to_parquet_chunked(zip_path, out_path):
    # reads CSV in chunks and writes to parquet incrementally
    total_rows = 0
    writer = None
    try:
        with ZipFile(zip_path) as file:
            csv_file = next(n for n in file.namelist() if n.endswith('csv'))
            with file.open(csv_file) as f:
                # read CSV
                for chunk in pd.read_csv(f, usecols=COLUMNS_KEEP, dtype=DTYPE_OVERRIDES, chunksize=CHUNK_ROWS, low_memory=False):
                    table = pa.Table.from_pandas(chunk, preserve_index=False)
                    if writer is None:
                        writer = pq.ParquetWriter(out_path, table.schema)
                    # write to parquet
                    writer.write_table(table)
                    total_rows += len(chunk)
    finally:
        if writer is not None:
              writer.close()
    return total_rows 

def download_month():
    # find latest month url
    try:
        url, year, month = get_latest_available_month()
    except NoNewDataError as e:
        raise RuntimeError(f"No new BTS data available: {e}") from e
    
    print(f"\nDownloading: {url}")
    zip_path = None
    parquet_path = None
    try:
        zip_path = download_zip_to_tempfile(url)
        print("Download complete. Converting to Parquet...")
        
        parquet_fd, parquet_path = tempfile.mkstemp(suffix=".parquet")
        os.close(parquet_fd)
        row_count = csv_to_parquet_chunked(zip_path, parquet_path)
        
        print(f"Converted {row_count:,} rows to Parquet.")
        return parquet_path, year, month
    except requests.RequestException as e:
        raise RuntimeError(f"Error during download: {e}") from e
    finally:
        # cleanup temp zip files
        if zip_path and os.path.exists(zip_path):
            os.remove(zip_path)

def land_parquet_gcs(parquet_path, year, month, bucket_name=GCS_BUCKET):  
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(f"raw/bts/year={year}/month={month:02d}/flights.parquet")
    blob.upload_from_filename(parquet_path, content_type="application/octet-stream")
     
    print(f"Wrote {parquet_path} -> {bucket_name}")
    
def run():
    parquet_path = None
    year = month = None
    try:
        parquet_path, year, month = download_month()
        land_parquet_gcs(parquet_path, year, month)
    except requests.HTTPError as e:
        raise RuntimeError(
            f"Failed for {year}-{month if month is None else f'{month:02d}'}: {e}. "
            "If this is the most recent month, BTS may not have published "
            "it yet. They typically lag 6-8 weeks behind month end."
        ) from e
    finally:
        # cleanup
        if parquet_path and os.path.exists(parquet_path):
            os.remove(parquet_path)
            
# if __name__ == "__main__":
#     run()