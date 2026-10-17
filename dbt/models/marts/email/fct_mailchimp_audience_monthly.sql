-- One row per audience per month: how the list grew. Deduplicated to the
-- latest pull per month — the current month is still changing, so a later
-- pull supersedes an earlier one.
select
    concat(list_id, '-', cast(month_start as string)) as audience_month_id,
    list_id,
    month_start,
    existing_subscribers,
    imported_subscribers,
    opt_in_subscribers,
    subscribed,
    unsubscribed,
    cleaned,
    pending,
    ingested_at

from {{ ref('stg_mailchimp_list_growth_monthly') }}
qualify row_number() over (partition by list_id, month_start order by ingested_at desc) = 1
