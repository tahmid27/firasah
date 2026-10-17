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
-- once per pull. invalidate_hard_deletes=True marks a donation_id as
-- no-longer-valid when it stops appearing in THIS query's result (e.g. it
-- was refunded and dropped out of the API response) — so this query must
-- return only the latest complete pull per page, not the accumulated
-- history. If it returned every donation ever seen, a refunded donation's
-- old rows would keep it in the result forever and the refund would never
-- be detected.
--
-- _ingested_at is stamped once per ingestion run (see load_raw_to_bigquery
-- in ingestion/common.py), so all rows from one pull share a value: it
-- works as a batch ID. dense_rank() = 1 keeps the whole newest batch per
-- page (row_number() would keep just one row). A pull fetches every page
-- of donations before loading anything, so a crashed run lands zero rows
-- and this never sees a half-finished batch.
--
-- Constraint: this relies on every pull being COMPLETE. Switching the
-- connector to incremental fetching ("only donations since last time")
-- would make every unseen donation look refunded. If full pulls ever get
-- too expensive, the answer is windowed delete-detection, not incremental
-- fetch bolted on.
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
qualify dense_rank() over (partition by page_short_name order by ingested_at desc) = 1

{% endsnapshot %}
