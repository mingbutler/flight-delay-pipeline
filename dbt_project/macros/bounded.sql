-- returns the column when it falls within [min_value, max_value], otherwise null
{% macro bounded(column_name, min_value, max_value) %}
    case
        when {{ column_name }} between {{ min_value }} and {{ max_value }} then {{ column_name }}
    end
{% endmacro %}
