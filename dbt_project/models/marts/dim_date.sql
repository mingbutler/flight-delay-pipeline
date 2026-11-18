with spine as (
    {{ dbt_utils.date_spine(
        datepart="day",
        start_date="cast('2018-01-01' as date)",
        end_date="cast('2027-01-01' as date)"
    ) }}
),

base as (
    select
        cast(date_day as date) as date_day,
        extract(year from date_day) as year,
        extract(month from date_day) as month,
        extract(day from date_day) as day,
        extract(dayofweek from date_day) as day_of_week,       -- 1=Sunday..7=Saturday in BigQuery
        -- which occurrence of this weekday within the month (1 = first Monday, etc.)
        div(extract(day from date_day) - 1, 7) + 1 as weekday_of_month,
        -- true when this is the last occurrence of this weekday in the month
        extract(month from date_add(cast(date_day as date), interval 7 day)) != extract(month from date_day) as is_last_weekday_of_month
    from spine
),

holidays as (
    select
        *,
        -- US federal holidays on their actual date
        case
            when month = 1  and day = 1                                        then "New Year's Day"
            when month = 1  and day_of_week = 2 and weekday_of_month = 3       then 'Martin Luther King Jr. Day'
            when month = 2  and day_of_week = 2 and weekday_of_month = 3       then "Washington's Birthday"
            when month = 5  and day_of_week = 2 and is_last_weekday_of_month   then 'Memorial Day'
            when month = 6  and day = 19 and year >= 2021                      then 'Juneteenth'
            when month = 7  and day = 4                                        then 'Independence Day'
            when month = 9  and day_of_week = 2 and weekday_of_month = 1       then 'Labor Day'
            when month = 10 and day_of_week = 2 and weekday_of_month = 2       then 'Columbus Day'
            when month = 11 and day = 11                                       then 'Veterans Day'
            when month = 11 and day_of_week = 5 and weekday_of_month = 4       then 'Thanksgiving Day'
            when month = 12 and day = 25                                       then 'Christmas Day'
        end as holiday_name,
        -- fixed-date holidays only, used for weekend-observance shifting below
        (month = 1 and day = 1)
            or (month = 6 and day = 19 and year >= 2021)
            or (month = 7 and day = 4)
            or (month = 11 and day = 11)
            or (month = 12 and day = 25) as is_fixed_holiday
    from base
),

observed as (
    select
        *,
        -- fixed-date holiday on Saturday is observed the Friday before; on Sunday, the Monday after
        case
            when day_of_week = 6 and lead(is_fixed_holiday) over (order by date_day)
                then lead(holiday_name) over (order by date_day) || ' (Observed)'
            when day_of_week = 2 and lag(is_fixed_holiday) over (order by date_day)
                then lag(holiday_name) over (order by date_day) || ' (Observed)'
        end as observed_holiday_name
    from holidays
)

select
    date_day,
    year,
    month,
    day,
    day_of_week,
    format_date('%A', date_day) as day_name,
    format_date('%B', date_day) as month_name,
    extract(quarter from date_day) as quarter,
    day_of_week in (1, 7) as is_weekend,

    holiday_name,
    holiday_name is not null as is_holiday,
    is_fixed_holiday,
    observed_holiday_name,
    -- day off for federal workers: the holiday itself on a weekday, or its observed weekday
    (holiday_name is not null and day_of_week not in (1, 7))
        or observed_holiday_name is not null as is_holiday_observed

from observed
