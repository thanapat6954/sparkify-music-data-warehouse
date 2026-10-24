{% macro days_between(later, earlier) -%}
{% if target.type == 'duckdb' %}datediff('day', {{ earlier }}, {{ later }}){% else %}({{ later }} - {{ earlier }}){% endif %}
{%- endmacro %}
