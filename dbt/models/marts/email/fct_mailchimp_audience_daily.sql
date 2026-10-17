-- One row per audience per day: subscribes, unsubscribes and email
-- activity. Deduplicated to the latest pull per day — each run re-pulls a
-- rolling window of recent days, and a later pull supersedes an earlier
-- one. This is the table for a daily subscribe/unsubscribe chart.
select
    concat(list_id, '-', cast(activity_date as string)) as audience_day_id,
    org_id,
    list_id,
    activity_date,
    new_subscribers,
    unsubscribes,
    new_subscribers - unsubscribes as net_subscribers,
    other_adds,
    other_removes,
    emails_sent,
    unique_opens,
    recipient_clicks,
    hard_bounces,
    soft_bounces,
    ingested_at

from {{ ref('stg_mailchimp_list_activity_daily') }}
qualify row_number() over (partition by org_id, list_id, activity_date order by ingested_at desc) = 1
