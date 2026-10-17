{# Like `unique`, but within each org_id rather than across the whole table. #}
{% test unique_per_org(model, column_name) %}

select
    org_id,
    {{ column_name }},
    count(*) as occurrences
from {{ model }}
where {{ column_name }} is not null
group by org_id, {{ column_name }}
having count(*) > 1

{% endtest %}
