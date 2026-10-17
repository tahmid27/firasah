{% snapshot justgiving_donations_snapshot %}

{{
    config(
        target_schema='firasah_dev',
        unique_key='snapshot_key',
        strategy='check',
        check_cols=['amount', 'currency_code', 'traffic_source'],
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
-- Tenant scoping: the snapshot's key is (org_id, donation_id), not the
-- donation ID alone, so two charities that ever share a JustGiving donation
-- ID can't overwrite each other's history. dbt snapshots key on a single
-- column, hence the combined snapshot_key. "Latest complete pull" is per
-- charity and page for the same reason.
select
    concat(org_id, '|', cast(donation_id as string)) as snapshot_key,
    org_id,
    donation_id,
    donor_name,
    amount,
    currency_code,
    donation_date,
    charity_id,
    traffic_source,
    page_short_name
from {{ ref('stg_justgiving_donations') }}
qualify dense_rank() over (
    partition by org_id, page_short_name order by ingested_at desc
) = 1

{% endsnapshot %}
