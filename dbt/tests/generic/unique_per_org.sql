{#
    Like dbt's built-in `unique` test, but per tenant: a value only has to be
    unique within one charity (org_id). Two charities can legitimately share
    a platform ID (e.g. both connected the same JustGiving event), so a
    global uniqueness test would be wrong, and dedup logic keyed on the ID
    alone would merge two tenants' rows.

    Usage in a model's YAML, on the column that must be unique per org:
        tests:
          - unique_per_org

    A generic test is just a query that returns the rows breaking the rule;
    dbt passes the test when it returns nothing.
#}
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
