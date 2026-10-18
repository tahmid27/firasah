-- One row per campaign per hour after sending (0-23), from the latest pull.
select
    concat(campaign_id, '-', cast(hours_after_send as string)) as campaign_hour_id,
    org_id,
    campaign_id,
    send_time,
    hour_start,
    hours_after_send,
    emails_sent,
    unique_opens,
    recipient_clicks,
    proxy_excluded_unique_opens,
    ingested_at

from (
    select
        *,
        timestamp_diff(hour_start, timestamp_trunc(send_time, hour), hour) as hours_after_send
    from {{ ref('stg_mailchimp_campaign_timeseries') }}
    qualify dense_rank() over (partition by org_id, campaign_id order by ingested_at desc) = 1
)
