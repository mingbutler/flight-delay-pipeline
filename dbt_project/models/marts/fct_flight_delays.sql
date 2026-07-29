select
    flight_date,
    carrier,
    Origin,
    Dest,
    historical_dep_delay,
    historical_dep_delay > 15 as is_delayed
from {{ ref('int_flights_joined') }}