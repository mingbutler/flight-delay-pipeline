select 
     h.flight_date,
    h.carrier,
    h.flight_number,
    h.Origin,
    h.Dest,

    h.scheduled_dep_time as historical_scheduled_dep_time,
    h.actual_dep_time as historical_actual_dep_time,
    h.dep_delay_minutes as historical_dep_delay,

    h.scheduled_arr_time as historical_scheduled_arr_time,
    h.actual_arr_time as historical_actual_arr_time,
    h.arr_delay_minutes as historical_arr_delay,

    h.is_cancelled,
    h.cancellation_code,
    h.is_diverted,

    l.actual_dep_time as live_actual_dep_time,
    l.actual_arr_time as live_actual_arr_time,
    l.flight_status as live_flight_status,

    -- no matching live records to historical data
    l.flight_number is not null as has_live_match

from {{ ref('stg_bts_ontime') }} h 
left join {{ ref('stg_live_flights') }} l 
    on h.carrier = l.carrier
    and h.flight_number = l.flight_number
    and h.flight_date = l.flight_date
    and h.Origin = l.Origin

