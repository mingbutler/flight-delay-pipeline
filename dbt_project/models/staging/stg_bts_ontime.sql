-- Data quality rules:
--   * rows missing any part of the flight key (date, carrier, flight number, origin, dest) are dropped
--   * airport / carrier codes are trimmed + upper-cased; malformed codes and origin = dest rows are dropped
--   * measures outside plausible bounds are nulled (row is kept so flight counts stay accurate)
--   * duplicate flights (same date, carrier, flight number, origin) are collapsed to one row

with source as (
    select * from {{ source('raw', 'bts_ontime') }}
),

cleaned as (
    select
        cast(FlightDate as date) as flight_date,
        upper(trim(Reporting_Airline)) as carrier,
        cast(safe_cast(Flight_Number_Reporting_Airline as int64) as string) as flight_number,
        upper(trim(Origin)) as Origin,
        upper(trim(Dest)) as Dest,

        {{ hhmm_to_time('CRSDepTime') }} as scheduled_dep_time,
        {{ hhmm_to_time('DepTime') }} as actual_dep_time,
        {{ bounded('DepDelayMinutes', 0, var('max_delay_minutes')) }} as dep_delay_minutes,
        {{ hhmm_to_time('CRSArrTime') }} as scheduled_arr_time,
        {{ hhmm_to_time('ArrTime') }} as actual_arr_time,
        {{ bounded('ArrDelayMinutes', 0, var('max_delay_minutes')) }} as arr_delay_minutes,

        Cancelled as is_cancelled,
        -- code is only meaningful on cancelled flights; blank strings -> null
        case when Cancelled = 1 then nullif(upper(trim(CancellationCode)), '') end as cancellation_code,
        Diverted as is_diverted,

        {{ bounded('Distance', 1, var('max_distance_miles')) }} as distance,

        {{ bounded('CarrierDelay', 0, var('max_delay_minutes')) }} as carrier_delay,
        {{ bounded('WeatherDelay', 0, var('max_delay_minutes')) }} as weather_delay,
        {{ bounded('NASDelay', 0, var('max_delay_minutes')) }} as nas_delay,
        {{ bounded('SecurityDelay', 0, var('max_delay_minutes')) }} as security_delay,
        {{ bounded('LateAircraftDelay', 0, var('max_delay_minutes')) }} as late_aircraft_delay
    from source
),

validated as (
    select *
    from cleaned
    where flight_date is not null
      and flight_date between date '{{ var("min_flight_date") }}' and current_date()
      and regexp_contains(carrier, r'^[A-Z0-9]{2}$')
      and flight_number is not null
      and regexp_contains(Origin, r'^[A-Z]{3}$')
      and regexp_contains(Dest, r'^[A-Z]{3}$')
      and Origin != Dest
      and is_cancelled in (0, 1)
      and is_diverted in (0, 1)
)

select *
from validated
qualify row_number() over (
    partition by flight_date, carrier, flight_number, Origin
    -- prefer the most complete record: flown over cancelled, then rows with actual times
    order by is_cancelled asc, actual_dep_time is null, actual_arr_time is null, scheduled_dep_time
) = 1
