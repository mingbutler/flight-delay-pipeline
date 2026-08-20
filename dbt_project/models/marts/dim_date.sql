with spine as (
    {{ dbt_utils.date_spine(
        datepart="day",
        start_date="cast('2018-01-01' as date)",
        end_date="cast('2027-01-01' as date)"
    ) }}
)

select
    cast(date_day as date) as date_day,
    extract(year from date_day) as year,
    extract(month from date_day) as month,
    extract(day from date_day) as day,
    extract(dayofweek from date_day) as day_of_week,       -- 1=Sunday..7=Saturday in BigQuery
    format_date('%A', date_day) as day_name,
    format_date('%B', date_day) as month_name,
    extract(quarter from date_day) as quarter,
    extract(dayofweek from date_day) in (1, 7) as is_weekend,

    -- simple fixed-date US holiday flags
    case
        when format_date('%m-%d', date_day) = '01-01' then true  -- New Year's Day
        when format_date('%m-%d', date_day) = '07-04' then true  -- July 4th
        when format_date('%m-%d', date_day) = '12-25' then true  -- Christmas
        when format_date('%m-%d', date_day) = '11-11' then true  -- Veterans Day
        else false
    end as is_fixed_holiday

from spine