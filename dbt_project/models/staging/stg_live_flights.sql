select
    dt as flight_date, -- partition column
    Reporting_Airline as carrier,
    regexp_extract(FlightNumber, r'(\d+)$') as flight_number, -- strips carrier prefix
    Origin,
    Dest,
    -- only need time of day from ISO local 
    time(timestamp(CRSDepTime)) as scheduled_dep_time,
    time(timestamp(DepTime)) as actual_dep_time,
    time(timestamp(CRSArrTime)) as scheduled_arr_time,
    time(timestamp(ArrTime)) as actual_arr_time,
    FlightStatus as flight_status,
    Direction as direction
from {{ source('raw', 'live_flights') }}