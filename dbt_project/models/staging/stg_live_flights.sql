select
    dt as flight_date, -- partition column
    Reporting_Airline as carrier,
    FlightNumber as flight_number,
    Origin,
    Dest,
    CRSDepTime as scheduled_dep_time,
    DepTime as actual_dep_time,
    CRSArrTime as scheduled_arr_time,
    ArrTime as actual_arr_time,
    FlightStatus as flight_status,
    Direction as direction
from {{ source('raw', 'live_flights') }}