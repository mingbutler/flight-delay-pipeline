select
    iata_code,
    airport_name,
    city,
    state,
    latitude,
    longitude
from {{ ref('airport_lookup') }}