-- Currently-active JustGiving donations, ready to chart. "Currently active"
-- means still present in the source as of the last snapshot run — a
-- donation that disappears from the API (e.g. refunded) gets invalidated
-- by the snapshot and drops out of this table automatically.
select
    donation_id,
    donor_name,
    amount,
    currency_code,
    donation_date,
    charity_id,
    donation_channel,
    page_short_name
from {{ ref('justgiving_donations_snapshot') }}
where dbt_valid_to is null
