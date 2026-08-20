select
    flight_date,
    carrier,
    Origin as origin_airport,
    Dest as dest_airport,

    historical_scheduled_dep_time,
    historical_actual_dep_time,
    historical_dep_delay,
    historical_dep_delay > 15 as is_dep_delayed,

    historical_scheduled_arr_time,
    historical_actual_arr_time,
    historical_arr_delay,
    historical_arr_delay > 15 as is_arr_delayed,

    is_cancelled,
    cancellation_code,
    is_diverted,

    live_flight_status,
    has_live_match
from {{ ref('int_flights_joined') }}