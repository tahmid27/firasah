-- One row per JustGiving fundraising page: its project, target and
-- JustGiving's own running totals, from the latest pull.
select
    org_id,
    page_short_name,
    coalesce(page_title, page_short_name) as fundraiser_name,
    event_name as project_name,
    owner_name,
    page_status,
    currency_code,
    fundraising_target,
    total_raised,
    total_estimated_gift_aid,
    donation_count,
    page_created_at,
    ingested_at

from {{ ref('stg_justgiving_pages') }}
qualify row_number() over (partition by org_id, page_short_name order by ingested_at desc) = 1
