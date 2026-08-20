select
    carrier_code,
    carrier_name
from {{ ref('carrier_lookup') }}