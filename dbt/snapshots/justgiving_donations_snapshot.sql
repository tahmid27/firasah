{% snapshot justgiving_donations_snapshot %}

{{
    config(
        target_schema='firasah_dev',
        unique_key='donation_id',
        strategy='check',
        check_cols=['amount', 'currency_code', 'donation_channel'],
        invalidate_hard_deletes=True,
    )
}}

-- raw_justgiving_donations is append-only, so the same donation can appear
-- more than once across pulls. A snapshot needs exactly one row per
-- unique_key on every run, so we take the most recently ingested version.
-- invalidate_hard_deletes=True is what actually solves the refund problem:
-- if a donation_id stops showing up here (e.g. it gets refunded and drops
-- out of the API response), dbt marks it as no-longer-valid instead of us
-- having to detect the disappearance ourselves.
select
    donation_id,
    donor_name,
    amount,
    currency_code,
    donation_date,
    charity_id,
    donation_channel,
    page_short_name
from {{ ref('stg_justgiving_donations') }}
qualify row_number() over (partition by donation_id order by ingested_at desc) = 1

{% endsnapshot %}
