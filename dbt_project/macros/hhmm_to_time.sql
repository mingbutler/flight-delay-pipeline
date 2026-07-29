{% macro hhmm_to_time(column_name) %}
    case
        when {{ column_name }} is null then null
        -- BTS uses 2400 to mean midnight; TIME type can't represent 24:00
        when {{ column_name }} = 2400 then time '00:00:00'
        else parse_time(
            '%H%M',
            lpad(cast(cast({{ column_name }} as int64) as string), 4, '0')
        )
    end
{% endmacro %}