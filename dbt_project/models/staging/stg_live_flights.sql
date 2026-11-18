-- Data quality rules:
--   * rows missing any part of the flight key (date, carrier, flight number, origin) are dropped
--   * airport / carrier codes are trimmed + upper-cased; malformed codes and origin = dest rows are dropped
--   * duplicate flights (same date, carrier, flight number, origin) are collapsed to one row,
--     e.g. a flight seen both as a departure and an arrival when several airports are fetched

with source as (
    select * from {{ source('raw', 'live_flights') }}
),

cleaned as (
    select
        dt as flight_date, -- partition column
        upper(trim(Reporting_Airline)) as carrier,
        -- strips carrier prefix and leading zeros so it matches BTS numbering
        cast(safe_cast(regexp_extract(FlightNumber, r'(\d+)$') as int64) as string) as flight_number,
        upper(trim(Origin)) as Origin,
        upper(trim(Dest)) as Dest,
        -- only need time of day from ISO local
        -- AeroDataBox 'local' does not include seconds
        -- safe nulls anything malformed
        time(safe.parse_timestamp('%Y-%m-%d %H:%M%Ez', CRSDepTime)) as scheduled_dep_time,
        time(safe.parse_timestamp('%Y-%m-%d %H:%M%Ez', DepTime)) as actual_dep_time,
        time(safe.parse_timestamp('%Y-%m-%d %H:%M%Ez', CRSArrTime)) as scheduled_arr_time,
        time(safe.parse_timestamp('%Y-%m-%d %H:%M%Ez', ArrTime)) as actual_arr_time,
        nullif(trim(FlightStatus), '') as flight_status,
        lower(trim(Direction)) as direction
    from source
),

validated as (
    select *
    from cleaned
    where flight_date is not null
      and regexp_contains(carrier, r'^[A-Z0-9]{2}$')
      and flight_number is not null
      and regexp_contains(Origin, r'^[A-Z]{3}$')
      and (Dest is null or regexp_contains(Dest, r'^[A-Z]{3}$'))
      and (Dest is null or Origin != Dest)
)

select *
from validated
qualify row_number() over (
    partition by flight_date, carrier, flight_number, Origin
    -- prefer rows with actual times, and the departure-side view for departure data
    order by actual_dep_time is null, actual_arr_time is null, direction = 'departure' desc
) = 1
