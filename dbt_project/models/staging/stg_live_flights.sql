select
    dt as flight_date, -- partition column
    Reporting_Airline as carrier,
    regexp_extract(FlightNumber, r'(\d+)$') as flight_number, -- strips carrier prefix
    Origin,
    Dest,
    -- only need time of day from ISO local 
    -- AeroDataBox 'local' does not include seconds
    -- safe nulls anything malformed
    time(safe.parse_timestamp('%Y-%m-%d %H:%M%Ez', CRSDepTime)) as scheduled_dep_time,
    time(safe.parse_timestamp('%Y-%m-%d %H:%M%Ez', DepTime)) as actual_dep_time,
    time(safe.parse_timestamp('%Y-%m-%d %H:%M%Ez', CRSArrTime)) as scheduled_arr_time,
    time(safe.parse_timestamp('%Y-%m-%d %H:%M%Ez', ArrTime)) as actual_arr_time,
    FlightStatus as flight_status,
    Direction as direction
from {{ source('raw', 'live_flights') }}